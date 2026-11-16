def emit(conn, key, kind):
    conn.execute('INSERT INTO events(key, kind) VALUES (?, ?)', (key, kind))


def history(conn, key):
    return [dict(row) for row in conn.execute(
        'SELECT key, kind FROM events WHERE key=? ORDER BY id', (key,))]
