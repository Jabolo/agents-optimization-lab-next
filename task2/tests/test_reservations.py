import concurrent.futures
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from inventory import Conflict, Service, Unavailable
from inventory.storage import connect, reservation, seed


class ReservationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'inventory.sqlite'
        self.conn = connect(self.path)
        self.addCleanup(self.conn.close)
        seed(self.conn, 'tea', 5)
        self.service = Service(self.conn)

    def reserve(self, key='a', qty=2, expires_at=20, now=10):
        return self.service.reserve(key, 'tea', qty, expires_at, now)

    def kinds(self, key):
        return [item['kind'] for item in self.service.events(key)]

    def reject_events(self, kind):
        # Known fixture constant, not participant input.
        self.conn.execute(f"""CREATE TRIGGER reject_event BEFORE INSERT ON events
            WHEN NEW.kind='{kind}' BEGIN SELECT RAISE(ABORT, 'event rejected'); END""")

    def test_reserve_and_exact_retry(self):
        result = self.reserve()
        self.assertEqual(result, {'key': 'a', 'sku': 'tea', 'qty': 2,
                                 'expires_at': 20, 'status': 'active'})
        self.assertEqual(self.reserve(), result)
        self.assertEqual(self.service.available('tea'), 3)
        self.assertEqual(self.kinds('a'), ['reserved'])

    def test_conflicting_identity(self):
        self.reserve()
        for args in [('a', 'tea', 3, 20, 10), ('a', 'cup', 2, 20, 10),
                     ('a', 'tea', 2, 21, 10)]:
            with self.subTest(args=args), self.assertRaises(Conflict):
                self.service.reserve(*args)
        self.assertEqual(self.service.available('tea'), 3)

    def test_validation_before_mutation(self):
        base = ['a', 'tea', 2, 20, 10]
        invalid = [(0, ''), (0, 1), (1, ''), (1, None), (2, 0), (2, -1),
                   (2, True), (2, 1.5), (3, 10), (3, True), (4, False), (4, 1.5)]
        for index, value in invalid:
            args = base.copy()
            args[index] = value
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.service.reserve(*args)
            self.assertEqual(self.service.available('tea'), 5)
            self.assertEqual(self.service.events('a'), [])

    def test_unavailable_does_not_consume_key(self):
        with self.assertRaises(Unavailable):
            self.reserve(qty=6)
        with self.assertRaises(Unavailable):
            self.service.reserve('a', 'missing', 1, 20, 10)
        self.assertEqual(self.reserve()['status'], 'active')

    def test_retry_still_validates_types(self):
        self.reserve(qty=1)
        with self.assertRaises(ValueError):
            self.reserve(qty=True)
        self.assertEqual(self.service.available('tea'), 4)
        self.assertEqual(self.kinds('a'), ['reserved'])

    def test_expiry_preserves_other_states_and_products(self):
        seed(self.conn, 'cup', 4)
        self.reserve('a', qty=2, expires_at=20)
        self.reserve('b', qty=1, expires_at=50)
        self.service.reserve('c', 'cup', 3, 20, 10)
        self.service.cancel('c')
        self.assertEqual(self.service.expire(30), 1)
        self.assertEqual(self.service.available('tea'), 4)
        self.assertEqual(self.service.available('cup'), 4)
        self.assertEqual(reservation(self.conn, 'b')['status'], 'active')
        self.assertEqual(self.kinds('c'), ['reserved', 'cancelled'])

    def test_cancel_once_and_retry_in_current_state(self):
        self.reserve()
        self.service.cancel('a')
        self.assertEqual(self.service.cancel('a')['status'], 'cancelled')
        self.assertEqual(self.reserve(now=30)['status'], 'cancelled')
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(self.kinds('a'), ['reserved', 'cancelled'])
        with self.assertRaises(Conflict):
            self.reserve(qty=1)

    def test_expiry_boundary_restores_stock_once(self):
        self.reserve()
        self.assertEqual(self.service.expire(19), 0)
        self.assertEqual(self.service.expire(20), 1)
        self.assertEqual(self.service.expire(21), 0)
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(self.reserve(now=30)['status'], 'expired')
        self.assertEqual(self.service.cancel('a')['status'], 'expired')
        self.assertEqual(self.kinds('a'), ['reserved', 'expired'])
        with self.assertRaises(Conflict):
            self.reserve(qty=1, now=30)

    def test_no_implicit_expiry(self):
        self.reserve(qty=5)
        with self.assertRaises(Unavailable):
            self.reserve(key='b', qty=1, expires_at=50, now=40)
        self.assertEqual(self.reserve(qty=5, now=40)['status'], 'active')

    def test_expire_validates_clock(self):
        for now in (True, 10.5, '20', None):
            with self.subTest(now=now), self.assertRaises(ValueError):
                self.service.expire(now)

    def test_unknown_lookup_and_cancel(self):
        with self.assertRaises(KeyError):
            self.service.available('missing')
        with self.assertRaises(KeyError):
            self.service.cancel('missing')

    def test_retry_survives_reopen(self):
        self.reserve()
        self.service.cancel('a')
        other = connect(self.path)
        self.addCleanup(other.close)
        service = Service(other)
        self.assertEqual(service.reserve('a', 'tea', 2, 20, 50)['status'], 'cancelled')
        self.assertEqual(service.available('tea'), 5)
        with self.assertRaises(Conflict):
            service.reserve('a', 'tea', 3, 20, 10)

    def test_reserve_rolls_back_when_event_fails(self):
        self.reject_events('reserved')
        with self.assertRaises(sqlite3.IntegrityError):
            self.reserve()
        self.assertEqual(self.service.available('tea'), 5)
        with self.assertRaises(KeyError):
            reservation(self.conn, 'a')
        self.assertEqual(self.kinds('a'), [])
        self.conn.execute('DROP TRIGGER reject_event')
        self.assertEqual(self.reserve()['status'], 'active')

    def test_cancel_rolls_back_when_event_fails(self):
        self.reserve()
        self.reject_events('cancelled')
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.cancel('a')
        self.assertEqual(reservation(self.conn, 'a')['status'], 'active')
        self.assertEqual(self.service.available('tea'), 3)
        self.assertEqual(self.kinds('a'), ['reserved'])

    def test_expire_entire_batch_rolls_back(self):
        self.reserve('a')
        self.reserve('b')
        self.conn.execute("""CREATE TRIGGER reject_event BEFORE INSERT ON events
            WHEN NEW.kind='expired' AND NEW.key='b'
            BEGIN SELECT RAISE(ABORT, 'event rejected'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.expire(21)
        for key in ('a', 'b'):
            self.assertEqual(reservation(self.conn, key)['status'], 'active')
            self.assertEqual(self.kinds(key), ['reserved'])
        self.assertEqual(self.service.available('tea'), 1)

    def test_competing_connections_preserve_stock(self):
        # Barrier starts requests together; OS ordering is deliberately unspecified.
        # Assertions concern invariants for every outcome, not a preferred winner.
        gate = threading.Barrier(8)

        def attempt(i):
            conn = connect(self.path)
            try:
                service = Service(conn)
                gate.wait(timeout=10)
                try:
                    service.reserve(str(i), 'tea', 2, 20, 10)
                    return True
                except Unavailable:
                    return False
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            successes = sum(pool.map(attempt, range(8)))
        self.assertEqual(successes, 2)
        self.assertEqual(self.service.available('tea'), 1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM reservations').fetchone()[0], 2)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0], 2)

    def test_same_key_competing_connections_allocate_once(self):
        gate = threading.Barrier(4)

        def attempt(_):
            conn = connect(self.path)
            try:
                gate.wait(timeout=10)
                return Service(conn).reserve('same', 'tea', 2, 20, 10)
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        self.assertTrue(all(item == results[0] for item in results))
        self.assertEqual(self.service.available('tea'), 3)
        self.assertEqual(self.kinds('same'), ['reserved'])
