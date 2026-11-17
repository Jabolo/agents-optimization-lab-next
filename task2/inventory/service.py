import hashlib
import json

from . import allocation, lifecycle
from .events import emit, history
from .storage import reservation


class Service:
    def __init__(self, conn):
        self.conn = conn
        self._rebuilds = {}

    def reserve(self, key, sku, qty, expires_at, now):
        return allocation.reserve(self.conn, key, sku, qty, expires_at, now)

    def cancel(self, key):
        return lifecycle.cancel(self.conn, key)

    def expire(self, now):
        return lifecycle.expire(self.conn, now)

    def amend(self, key, change_id, qty, expires_at, expected_version, now):
        item = reservation(self.conn, key)
        self.conn.execute('UPDATE stock SET available=available+? WHERE sku=?',
                          (item['qty'] - qty, item['sku']))
        self.conn.execute('UPDATE reservations SET qty=?,expires_at=?,version=version+1 WHERE key=?',
                          (qty, expires_at, key))
        emit(self.conn, key, 'amended')
        return reservation(self.conn, key)

    def available(self, sku):
        return self.conn.execute('SELECT available FROM stock WHERE sku=?', (sku,)).fetchone()[0]

    def events(self, key):
        return history(self.conn, key)

    def snapshots(self):
        return [reservation(self.conn, row['key']) for row in self.conn.execute(
            'SELECT key FROM reservations ORDER BY key')]

    def dispatch(self, publisher, limit=100):
        # Initial implementation assumes a successful local read implies delivery.
        rows = self.conn.execute('SELECT * FROM events WHERE published=0 ORDER BY id LIMIT ?',
                                 (limit,)).fetchall()
        for row in rows:
            self.conn.execute('UPDATE events SET published=1 WHERE id=?', (row['id'],))
            publisher({key: row[key] for key in ('id', 'key', 'sku', 'qty', 'expires_at',
                                                   'status', 'version', 'kind')})
        return len(rows)

    @staticmethod
    def _digest(items):
        content = json.dumps(items, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def _page(items, field, after, limit):
        items = [item for item in items if after is None or item[field] > after]
        page = items[:limit]
        return {'items': page, 'next': page[-1][field] if len(items) > limit and page else None}

    def begin_rebuild(self, token):
        snapshots = self.snapshots()
        watermark = self.conn.execute('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0]
        manifest = {'token': token, 'watermark': watermark, 'count': len(snapshots),
                    'digest': self._digest(snapshots), 'seen_count': 0, 'seen_digest': self._digest([])}
        self._rebuilds[token] = {'manifest': manifest, 'snapshots': snapshots, 'events': []}
        return manifest

    def snapshot_page(self, token, after=None, limit=100):
        return self._page(self._rebuilds[token]['snapshots'], 'key', after, limit)

    def seen_page(self, token, after=None, limit=100):
        return self._page([], 'id', after, limit)

    def fence_rebuild(self, token):
        entry = self._rebuilds[token]
        rows = self.conn.execute('SELECT * FROM events WHERE id>? ORDER BY id',
                                 (entry['manifest']['watermark'],)).fetchall()
        fields = ('id', 'key', 'sku', 'qty', 'expires_at', 'status', 'version', 'kind')
        entry['events'] = [{field: row[field] for field in fields} for row in rows]
        return {'token': token, 'watermark': entry['manifest']['watermark'],
                'through': rows[-1]['id'] if rows else entry['manifest']['watermark'],
                'event_ids': [row['id'] for row in rows], 'digest': self._digest(entry['events'])}

    def rebuild_events(self, token, after=None, limit=100):
        return self._page(self._rebuilds[token]['events'], 'id', after, limit)
