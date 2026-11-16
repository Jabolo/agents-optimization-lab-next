from .events import emit
from .storage import reservation


def cancel(conn, key):
    item = reservation(conn, key)
    conn.execute('UPDATE stock SET available=available+? WHERE sku=?',
                 (item['qty'], item['sku']))
    conn.execute("UPDATE reservations SET status='cancelled' WHERE key=?", (key,))
    emit(conn, key, 'cancelled')
    return reservation(conn, key)


def expire(conn, now):
    items = conn.execute(
        "SELECT * FROM reservations WHERE status='active' AND expires_at < ?", (now,)
    ).fetchall()
    for item in items:
        conn.execute("UPDATE reservations SET status='expired' WHERE key=?", (item['key'],))
        emit(conn, item['key'], 'expired')
    return len(items)
