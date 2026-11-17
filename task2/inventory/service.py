from . import allocation, lifecycle
from .events import emit, history
from .storage import reservation


class Service:
    def __init__(self, conn):
        self.conn = conn

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
