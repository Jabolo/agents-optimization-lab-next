import sqlite3


class MigrationError(ValueError):
    pass


def connect(path, *, migration_hook=None):
    conn = sqlite3.connect(path, isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    fresh = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='stock'").fetchone()[0] == 0
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS stock(sku TEXT PRIMARY KEY, available INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS reservations(
            key TEXT PRIMARY KEY, sku TEXT NOT NULL, qty INTEGER NOT NULL,
            expires_at INTEGER NOT NULL, status TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            original_qty INTEGER NOT NULL, original_expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS amendments(
            key TEXT NOT NULL, change_id TEXT NOT NULL, qty INTEGER NOT NULL,
            expires_at INTEGER NOT NULL, expected_version INTEGER NOT NULL,
            PRIMARY KEY(key, change_id));
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY, key TEXT NOT NULL, kind TEXT NOT NULL,
            sku TEXT, qty INTEGER, expires_at INTEGER, status TEXT,
            version INTEGER, published INTEGER NOT NULL DEFAULT 0);
    ''')
    if fresh:
        conn.execute('PRAGMA user_version=2')
    return conn


def seed(conn, sku, quantity):
    conn.execute('INSERT INTO stock VALUES (?, ?)', (sku, quantity))


def reservation(conn, key):
    row = conn.execute('SELECT key,sku,qty,expires_at,status,version FROM reservations WHERE key=?', (key,)).fetchone()
    if row is None:
        raise KeyError(key)
    return dict(row)
