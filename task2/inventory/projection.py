"""The old reporting process trusts every delivery and remembers only latest state."""
import json
import sqlite3

from .allocation import Conflict


class Gap(ValueError):
    pass


def connect_projection(path):
    conn = sqlite3.connect(path, isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.executescript('''CREATE TABLE IF NOT EXISTS projection(key TEXT PRIMARY KEY, body TEXT NOT NULL);
                         CREATE TABLE IF NOT EXISTS seen(id INTEGER PRIMARY KEY, body TEXT NOT NULL);''')
    return conn


class Projection:
    def __init__(self, conn, *, apply_hook=None, cutover_hook=None):
        self.conn = conn
        self.apply_hook = apply_hook
        self.cutover_hook = cutover_hook
        self._staging = {}

    def bootstrap(self, snapshot):
        self.conn.execute('INSERT OR REPLACE INTO projection VALUES (?,?)',
                          (snapshot['key'], json.dumps(snapshot)))
        return snapshot

    def get(self, key):
        row = self.conn.execute('SELECT body FROM projection WHERE key=?', (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row['body'])

    def apply(self, envelope):
        snapshot = {k: envelope[k] for k in ('key', 'sku', 'qty', 'expires_at', 'status', 'version')}
        self.bootstrap(snapshot)
        return True

    def view(self):
        return [json.loads(row['body']) for row in self.conn.execute('SELECT body FROM projection ORDER BY key')]

    def begin_rebuild(self, manifest):
        self._staging[manifest['token']] = {'manifest': manifest, 'events': {}}
        return True

    def stage_snapshot(self, token, snapshot):
        self.bootstrap(snapshot)
        return True

    def stage_seen(self, token, envelope):
        return True

    def stage_event(self, token, envelope):
        self._staging[token]['events'][envelope['id']] = envelope
        return True

    def cutover(self, token, fence):
        if self.cutover_hook:
            self.cutover_hook(self.conn, token)
        return True

    def pending(self, token):
        return list(self._staging[token]['events'].values())

    def ack_pending(self, token, event_id):
        del self._staging[token]['events'][event_id]
        return True

    def repair_staged(self, token, category, expected, replacement=None):
        # A local repair used to affect the visible projection immediately.
        if replacement is not None and category == 'snapshot':
            self.bootstrap(replacement)
        return True

    def quarantined(self, token):
        return []

    def repair_manifest(self, token, expected, replacement):
        self._staging[token]['manifest'] = replacement
        return True
