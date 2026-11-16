from . import allocation, lifecycle
from .events import history


class Service:
    def __init__(self, conn):
        self.conn = conn

    def reserve(self, key, sku, qty, expires_at, now):
        return allocation.reserve(self.conn, key, sku, qty, expires_at, now)

    def cancel(self, key):
        return lifecycle.cancel(self.conn, key)

    def expire(self, now):
        return lifecycle.expire(self.conn, now)

    def available(self, sku):
        return self.conn.execute('SELECT available FROM stock WHERE sku=?', (sku,)).fetchone()[0]

    def events(self, key):
        return history(self.conn, key)
