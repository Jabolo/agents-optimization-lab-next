from .events import emit
from .storage import reservation


class Conflict(ValueError):
    pass


class Unavailable(ValueError):
    pass


def reserve(conn, key, sku, qty, expires_at, now):
    # Legacy retry path: a completed request must not be charged again.
    existing = conn.execute('SELECT * FROM reservations WHERE key=?', (key,)).fetchone()
    if existing:
        return dict(existing)
    row = conn.execute('SELECT available FROM stock WHERE sku=?', (sku,)).fetchone()
    if row is None or row['available'] < qty:
        raise Unavailable(sku)
    conn.execute('UPDATE stock SET available=? WHERE sku=?', (row['available'] - qty, sku))
    conn.execute('INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                 (key, sku, qty, expires_at, 'active', 1, qty, expires_at))
    emit(conn, key, 'reserved')
    return reservation(conn, key)
