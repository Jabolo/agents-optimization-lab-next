import concurrent.futures
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from inventory import Conflict, Service
from inventory.storage import MigrationError, connect, seed
from inventory.projection import Gap, Projection, connect_projection


LEGACY_SCHEMA = '''
PRAGMA user_version=1;
CREATE TABLE stock(sku TEXT PRIMARY KEY, available INTEGER NOT NULL);
CREATE TABLE reservations(key TEXT PRIMARY KEY, sku TEXT NOT NULL, qty INTEGER NOT NULL,
                          expires_at INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE events(id INTEGER PRIMARY KEY, key TEXT NOT NULL, kind TEXT NOT NULL);
'''


def legacy(path):
    conn = sqlite3.connect(path, isolation_level=None)
    conn.executescript(LEGACY_SCHEMA)
    conn.executemany('INSERT INTO stock VALUES (?,?)', [('tea', 7), ('cup', 4)])
    conn.executemany('INSERT INTO reservations VALUES (?,?,?,?,?)', [
        ('old-1', 'tea', 3, 20, 'active'), ('old-2', 'cup', 1, 30, 'cancelled')])
    conn.executemany('INSERT INTO events VALUES (?,?,?)', [(10, 'old-1', 'reserved'),
                                                           (12, 'old-2', 'reserved'),
                                                           (13, 'old-2', 'cancelled')])
    conn.close()


def disk_state(path):
    conn = sqlite3.connect(path)
    try:
        schema = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        tables = {}
        for table in ('stock', 'reservations', 'events'):
            tables[table] = conn.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
        return schema, version, tables
    finally:
        conn.close()


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'legacy.sqlite'
        legacy(self.path)

    def test_upgrade_preserves_data_history_ids_and_request_identity(self):
        conn = connect(self.path)
        self.addCleanup(conn.close)
        svc = Service(conn)
        self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertEqual(svc.available('tea'), 7)
        original = {'key': 'old-1', 'sku': 'tea', 'qty': 3, 'expires_at': 20,
                    'status': 'active', 'version': 1}
        self.assertEqual(svc.reserve('old-1', 'tea', 3, 20, 99), original)
        self.assertEqual(svc.events('old-2'), [{'key': 'old-2', 'kind': 'reserved'},
                                               {'key': 'old-2', 'kind': 'cancelled'}])
        with self.assertRaises(Conflict):
            svc.reserve('old-1', 'tea', 2, 20, 10)
        delivered = []
        self.assertEqual(svc.dispatch(delivered.append), 0)
        self.assertEqual(delivered, [])
        svc.amend('old-1', 'change', 2, 40, 1, 10)
        self.assertEqual(svc.reserve('old-1', 'tea', 3, 20, 99)['qty'], 2)
        self.assertEqual(svc.dispatch(delivered.append), 1)
        self.assertGreater(delivered[0]['id'], 0)
        self.assertNotIn(delivered[0]['id'], (10, 12, 13))
        self.assertEqual((delivered[0]['key'], delivered[0]['version'], delivered[0]['kind']),
                         ('old-1', 2, 'amended'))
        conn.close()
        reopened = connect(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual(Service(reopened).dispatch(delivered.append), 0)
        self.assertEqual(Service(reopened).available('tea'), 8)
        self.assertEqual(Service(reopened).reserve('old-1', 'tea', 3, 20, 99)['version'], 2)

    def test_reopen_is_idempotent_and_no_synthetic_events(self):
        for _ in range(3):
            conn = connect(self.path)
            try:
                self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 2)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM events').fetchone()[0], 3)
                self.assertEqual(Service(conn).available('tea'), 7)
            finally:
                conn.close()

    def test_mid_migration_interruption_rolls_back_schema_and_rows(self):
        before = disk_state(self.path)
        calls = []

        def fail_before_commit(conn):
            calls.append(conn)
            raise RuntimeError('simulated interruption before commit')

        with self.assertRaisesRegex(RuntimeError, 'simulated interruption'):
            conn = connect(self.path, migration_hook=fail_before_commit)
            conn.close()
        self.assertEqual(len(calls), 1)
        self.assertEqual(disk_state(self.path), before)
        conn = connect(self.path)
        self.addCleanup(conn.close)
        self.assertEqual(Service(conn).reserve('old-1', 'tea', 3, 20, 99)['version'], 1)

    def test_invalid_legacy_data_fails_closed_without_partial_upgrade(self):
        for sql, args in [
            ("UPDATE stock SET available=-1 WHERE sku='tea'", ()),
            ("UPDATE reservations SET qty=0 WHERE key='old-1'", ()),
            ("UPDATE reservations SET qty=1.5 WHERE key='old-1'", ()),
            ("UPDATE reservations SET expires_at=1.5 WHERE key='old-1'", ()),
            ("UPDATE reservations SET status='pending' WHERE key='old-1'", ()),
            ("UPDATE reservations SET sku='missing' WHERE key='old-1'", ()),
            ("UPDATE reservations SET key='' WHERE key='old-1'", ()),
            ("UPDATE stock SET available=9223372036854775807 WHERE sku='tea'", ()),
        ]:
            with self.subTest(sql=sql):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / 'bad.sqlite'
                    legacy(path)
                    conn = sqlite3.connect(path, isolation_level=None)
                    conn.execute(sql, args)
                    conn.close()
                    before = disk_state(path)
                    with self.assertRaises(MigrationError):
                        conn = connect(path)
                        conn.close()
                    self.assertEqual(disk_state(path), before)

    def test_sqlite_exception_during_migration_propagates_and_rolls_back(self):
        for error_type in (sqlite3.OperationalError, sqlite3.IntegrityError):
            with self.subTest(error_type=error_type):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / 'old.sqlite'
                    legacy(path)
                    before = disk_state(path)

                    def fail(conn):
                        raise error_type('injected SQLite failure')

                    with self.assertRaises(error_type):
                        conn = connect(path, migration_hook=fail)
                        conn.close()
                    self.assertEqual(disk_state(path), before)
                    conn = connect(path)
                    try:
                        self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 2)
                        self.assertEqual(Service(conn).available('tea'), 7)
                    finally:
                        conn.close()

    def test_unsupported_and_unversioned_nonempty_database_rejected(self):
        for version in (0, 3, 999):
            with self.subTest(version=version):
                conn = sqlite3.connect(self.path, isolation_level=None)
                conn.execute(f'PRAGMA user_version={version}')
                conn.close()
                before = disk_state(self.path)
                with self.assertRaises(MigrationError):
                    conn = connect(self.path)
                    conn.close()
                self.assertEqual(disk_state(self.path), before)

    def test_two_connections_can_race_to_upgrade(self):
        gate = threading.Barrier(4)

        def open_one(_):
            gate.wait(timeout=10)
            conn = connect(self.path)
            try:
                return (conn.execute('PRAGMA user_version').fetchone()[0],
                        Service(conn).available('tea'),
                        conn.execute('SELECT COUNT(*) FROM events').fetchone()[0])
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(open_one, range(4)))
        self.assertEqual(results, [(2, 7, 3)] * 4)

    def test_legacy_negative_ids_retained_and_new_event_monotonic(self):
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.execute("INSERT INTO events VALUES (-5,'old-1','legacy')")
        conn.close()
        conn = connect(self.path)
        self.addCleanup(conn.close)
        svc = Service(conn)
        svc.reserve('new', 'tea', 1, 100, 10)
        ids = [row[0] for row in conn.execute('SELECT id FROM events ORDER BY id')]
        self.assertEqual(ids[:4], [-5, 10, 12, 13])
        self.assertGreater(ids[4], 13)

    def test_event_id_exhaustion_rolls_back_transition(self):
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.execute("INSERT INTO events VALUES (9223372036854775807,'old-1','legacy')")
        conn.close()
        conn = connect(self.path)
        self.addCleanup(conn.close)
        svc = Service(conn)
        before = svc.snapshots()
        with self.assertRaises(Conflict):
            svc.reserve('new', 'tea', 1, 100, 10)
        self.assertEqual(svc.snapshots(), before)
        self.assertEqual(svc.available('tea'), 7)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_path = self.root / 'source.sqlite'
        self.projection_path = self.root / 'projection.sqlite'
        self.conn = connect(self.source_path)
        self.addCleanup(self.conn.close)
        seed(self.conn, 'tea', 10)
        self.svc = Service(self.conn)
        self.pconn = connect_projection(self.projection_path)
        self.addCleanup(self.pconn.close)
        self.projection = Projection(self.pconn)

    def test_envelopes_capture_each_transition_not_current_state(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        self.svc.amend('a', 'x', 3, 30, 1, 10)
        self.svc.cancel('a')
        sent = []
        self.assertEqual(self.svc.dispatch(sent.append, 2), 2)
        self.assertEqual(self.svc.dispatch(sent.append), 1)
        self.assertEqual(self.svc.dispatch(sent.append), 0)
        self.assertEqual([e['kind'] for e in sent], ['reserved', 'amended', 'cancelled'])
        self.assertEqual([e['version'] for e in sent], [1, 2, 3])
        self.assertEqual([e['qty'] for e in sent], [2, 3, 3])
        self.assertEqual([e['status'] for e in sent], ['active', 'active', 'cancelled'])
        self.assertEqual([e['expires_at'] for e in sent], [20, 30, 30])
        self.assertEqual(len({e['id'] for e in sent}), 3)
        for event in sent:
            self.assertEqual(set(event), {'id', 'key', 'sku', 'qty', 'expires_at',
                                          'status', 'version', 'kind'})
            self.assertTrue(self.projection.apply(event))
        self.assertEqual(self.projection.get('a'), self.svc.snapshots()[0])

    def test_lost_ack_redelivery_after_both_databases_reopen(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        seen = []

        def deliver_then_lose_ack(event):
            seen.append(event)
            self.assertTrue(self.projection.apply(event))
            raise TimeoutError('ACK lost after remote commit')

        with self.assertRaises(TimeoutError):
            self.svc.dispatch(deliver_then_lose_ack)
        self.conn.close()
        self.pconn.close()
        self.conn = connect(self.source_path)
        self.pconn = connect_projection(self.projection_path)
        self.addCleanup(self.conn.close)
        self.addCleanup(self.pconn.close)
        self.svc, self.projection = Service(self.conn), Projection(self.pconn)
        results = []

        def retry(event):
            seen.append(event)
            results.append(self.projection.apply(event))

        self.assertEqual(self.svc.dispatch(retry), 1)
        self.assertEqual(results, [False])
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(self.projection.get('a')['version'], 1)
        self.assertEqual(self.svc.dispatch(retry), 0)

    def test_delivery_failure_keeps_previous_ack_only(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        self.svc.reserve('b', 'tea', 1, 30, 10)
        seen = []

        def second_fails(event):
            seen.append(event)
            if event['key'] == 'b':
                raise ConnectionError('unavailable')

        with self.assertRaises(ConnectionError):
            self.svc.dispatch(second_fails)
        later = []
        self.assertEqual(self.svc.dispatch(later.append), 1)
        self.assertEqual([e['key'] for e in later], ['b'])
        self.assertEqual(seen[-1], later[0])

    def test_invalid_limit_does_not_call_publisher(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        seen = []
        for limit in (0, -1, True, 1.5, '1', None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.svc.dispatch(seen.append, limit)
        self.assertEqual(seen, [])
        self.assertEqual(self.svc.dispatch(seen.append), 1)

    def test_outbox_failure_rolls_back_state_and_no_delivery(self):
        self.conn.execute("""CREATE TRIGGER reject_event BEFORE INSERT ON events
            WHEN NEW.kind='reserved' BEGIN SELECT RAISE(ABORT, 'outbox rejected'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.svc.reserve('a', 'tea', 2, 20, 10)
        self.assertEqual(self.svc.available('tea'), 10)
        self.assertEqual(self.svc.snapshots(), [])
        sent = []
        self.assertEqual(self.svc.dispatch(sent.append), 0)
        self.assertEqual(sent, [])

    def test_retries_and_rejections_do_not_emit_new_notifications(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        self.svc.reserve('a', 'tea', 2, 20, 30)
        with self.assertRaises(Conflict):
            self.svc.reserve('a', 'tea', 3, 20, 10)
        sent = []
        self.assertEqual(self.svc.dispatch(sent.append), 1)
        self.assertEqual(len(sent), 1)

    def test_out_of_order_gap_does_not_consume_event_id(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        self.svc.amend('a', 'x', 3, 30, 1, 10)
        sent = []
        self.svc.dispatch(sent.append)
        with self.assertRaises(Gap):
            self.projection.apply(sent[1])
        with self.assertRaises(KeyError):
            self.projection.get('a')
        self.assertTrue(self.projection.apply(sent[0]))
        self.assertTrue(self.projection.apply(sent[1]))
        self.assertFalse(self.projection.apply(sent[0]))
        self.assertEqual(self.projection.get('a')['version'], 2)

    def test_conflicting_duplicate_and_new_id_for_old_version_rejected(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        sent = []
        self.svc.dispatch(sent.append)
        event = sent[0]
        self.assertTrue(self.projection.apply(event))
        with self.assertRaises(Conflict):
            self.projection.apply({**event, 'qty': 9})
        with self.assertRaises(Gap):
            self.projection.apply({**event, 'id': event['id'] + 100})
        self.assertEqual(self.projection.get('a')['qty'], 2)
        self.assertFalse(self.projection.apply(event))

    def test_projection_hook_failure_rolls_back_dedup_and_state(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        sent = []
        self.svc.dispatch(sent.append)
        calls = []

        def interrupted(conn, envelope):
            calls.append(envelope)
            raise RuntimeError('consumer interrupted before commit')

        interrupted_projection = Projection(self.pconn, apply_hook=interrupted)
        with self.assertRaisesRegex(RuntimeError, 'consumer interrupted'):
            interrupted_projection.apply(sent[0])
        self.assertEqual(calls, [sent[0]])
        with self.assertRaises(KeyError):
            self.projection.get('a')
        self.pconn.close()
        self.pconn = connect_projection(self.projection_path)
        self.addCleanup(self.pconn.close)
        self.projection = Projection(self.pconn)
        self.assertTrue(self.projection.apply(sent[0]))
        self.assertFalse(self.projection.apply(sent[0]))
        self.assertEqual(self.projection.get('a')['version'], 1)

    def test_projection_hook_only_runs_for_new_success(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        self.svc.amend('a', 'x', 3, 30, 1, 10)
        sent = []
        self.svc.dispatch(sent.append)
        calls = []
        projection = Projection(self.pconn, apply_hook=lambda conn, envelope: calls.append(envelope))
        self.assertTrue(projection.apply(sent[0]))
        self.assertFalse(projection.apply(sent[0]))
        with self.assertRaises(Conflict):
            projection.apply({**sent[0], 'qty': 9})
        with self.assertRaises(Gap):
            projection.apply({**sent[1], 'version': 4})
        self.assertEqual(calls, [sent[0]])
        self.assertTrue(projection.apply(sent[1]))
        self.assertEqual(calls, sent)

    def test_two_projection_connections_deduplicate_same_delivery(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        sent = []
        self.svc.dispatch(sent.append)
        gate = threading.Barrier(2)

        def apply_one(_):
            conn = connect_projection(self.projection_path)
            try:
                gate.wait(timeout=10)
                return Projection(conn).apply(sent[0])
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply_one, range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.projection.get('a')['version'], 1)
        self.assertFalse(self.projection.apply(sent[0]))

    def test_bootstrap_is_idempotent_and_conflict_safe(self):
        self.svc.reserve('b', 'tea', 1, 20, 10)
        self.svc.reserve('a', 'tea', 2, 30, 10)
        snapshots = self.svc.snapshots()
        self.assertEqual([item['key'] for item in snapshots], ['a', 'b'])
        for snapshot in snapshots:
            self.assertEqual(self.projection.bootstrap(snapshot), snapshot)
            self.assertEqual(self.projection.bootstrap(snapshot), snapshot)
        with self.assertRaises(Conflict):
            self.projection.bootstrap({**snapshots[0], 'qty': 9})
        self.assertEqual(self.projection.get('a'), snapshots[0])

    def test_signed_64_bit_input_validation_precedes_retry_or_mutation(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        before = self.svc.snapshots()
        bad = 2**63
        reserve_args = [('a', 'tea', bad, 20, 10), ('a', 'tea', 2, bad, 10),
                        ('a', 'tea', 2, 20, -bad - 1)]
        for args in reserve_args:
            with self.subTest(args=args):
                with self.assertRaises(ValueError) as caught:
                    self.svc.reserve(*args)
                self.assertIs(type(caught.exception), ValueError)
                self.assertEqual(self.svc.snapshots(), before)
        amendment_args = [('a', 'x', bad, 30, 1, 10),
                          ('a', 'x', 1, bad, 1, 10),
                          ('a', 'x', 1, 30, bad, 10),
                          ('a', 'x', 1, 30, 1, -bad - 1)]
        for args in amendment_args:
            with self.subTest(args=args):
                with self.assertRaises(ValueError) as caught:
                    self.svc.amend(*args)
                self.assertIs(type(caught.exception), ValueError)
                self.assertEqual(self.svc.snapshots(), before)
        with self.assertRaises(ValueError) as caught:
            self.svc.expire(bad)
        self.assertIs(type(caught.exception), ValueError)
        with self.assertRaises(ValueError) as caught:
            self.svc.dispatch(lambda event: None, bad)
        self.assertIs(type(caught.exception), ValueError)
        self.assertEqual(self.svc.available('tea'), 8)
        self.assertEqual(self.svc.events('a'), [{'key': 'a', 'kind': 'reserved'}])

    def test_projection_rejects_malformed_envelopes_before_lookup(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        sent = []
        self.svc.dispatch(sent.append)
        event = sent[0]
        bad_events = [{**event, 'id': True}, {**event, 'id': 2**63},
                      {**event, 'key': ''}, {**event, 'sku': None},
                      {**event, 'qty': True}, {**event, 'qty': 0},
                      {**event, 'expires_at': 2**63}, {**event, 'version': True},
                      {**event, 'version': 2**63}, {**event, 'kind': 'other'},
                      {**event, 'status': 'missing'}, {**event, 'extra': 1},
                      {key: value for key, value in event.items() if key != 'sku'}, None]
        for bad in bad_events:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as caught:
                    self.projection.apply(bad)
                self.assertIs(type(caught.exception), ValueError)
                with self.assertRaises(KeyError):
                    self.projection.get('a')
        self.assertTrue(self.projection.apply(event))
        for bad in ({**event, 'id': True}, {**event, 'qty': True},
                    {**event, 'extra': 1}):
            with self.subTest(replay=bad):
                with self.assertRaises(ValueError) as caught:
                    self.projection.apply(bad)
                self.assertIs(type(caught.exception), ValueError)
        self.assertFalse(self.projection.apply(event))

    def test_surrogate_text_is_rejected_before_sql_or_identity_lookup(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        malformed = '\ud800'
        actions = [lambda: self.svc.reserve(malformed, 'tea', 1, 20, 10),
                   lambda: self.svc.reserve('b', malformed, 1, 20, 10),
                   lambda: self.svc.amend('a', malformed, 1, 30, 1, 10),
                   lambda: self.svc.begin_rebuild(malformed)]
        for action in actions:
            with self.subTest(action=action):
                with self.assertRaises(ValueError) as caught:
                    action()
                self.assertIs(type(caught.exception), ValueError)
        self.assertEqual(self.svc.available('tea'), 8)
        self.assertEqual(self.svc.events('a'), [{'key': 'a', 'kind': 'reserved'}])

    def test_projection_rejects_malformed_bootstrap_without_mutation(self):
        self.svc.reserve('a', 'tea', 2, 20, 10)
        snapshot = self.svc.snapshots()[0]
        for bad in ({**snapshot, 'qty': True}, {**snapshot, 'version': 2**63},
                    {**snapshot, 'status': 'missing'}, {**snapshot, 'extra': 1}, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as caught:
                    self.projection.bootstrap(bad)
                self.assertIs(type(caught.exception), ValueError)
                with self.assertRaises(KeyError):
                    self.projection.get('a')
        self.assertEqual(self.projection.bootstrap(snapshot), snapshot)

    def test_migrated_snapshot_bootstrap_then_postupgrade_delivery(self):
        path = self.root / 'old.sqlite'
        legacy(path)
        conn = connect(path)
        self.addCleanup(conn.close)
        svc = Service(conn)
        for snapshot in svc.snapshots():
            self.projection.bootstrap(snapshot)
        svc.amend('old-1', 'x', 2, 40, 1, 10)
        self.assertEqual(svc.dispatch(self.projection.apply), 1)
        self.assertEqual(self.projection.get('old-1'), svc.snapshots()[0])
        self.assertEqual(self.projection.get('old-1')['version'], 2)
