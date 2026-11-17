import concurrent.futures
import sqlite3
import threading
import unittest

import test_reservations as base
from inventory import Conflict, Service, Unavailable
from inventory.storage import connect, reservation


class AmendmentTests(unittest.TestCase):
    setUp = base.ReservationsTests.setUp
    reserve = base.ReservationsTests.reserve
    kinds = base.ReservationsTests.kinds
    reject_events = base.ReservationsTests.reject_events

    def amend(self, change='x', qty=3, expiry=30, version=1, now=10, key='a'):
        return self.service.amend(key, change, qty, expiry, version, now)

    def parallel(self, *operations):
        gate = threading.Barrier(len(operations))

        def run(operation):
            conn = connect(self.path)
            try:
                gate.wait(timeout=10)
                try:
                    return ('ok', operation(Service(conn)))
                except Conflict:
                    return ('conflict', None)
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(run, operations))

    def test_increase_decrease_noop_and_event_order(self):
        self.reserve()
        self.assertEqual(self.amend()['version'], 2)
        self.assertEqual(self.service.available('tea'), 2)
        item = self.amend('y', qty=1, expiry=40, version=2)
        self.assertEqual(item, {'key': 'a', 'sku': 'tea', 'qty': 1,
                                'expires_at': 40, 'status': 'active', 'version': 3})
        self.assertEqual(self.service.available('tea'), 4)
        self.assertEqual(self.amend('z', qty=1, expiry=40, version=3)['version'], 4)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended', 'amended', 'amended'])

    def test_replay_returns_current_state_not_old_snapshot(self):
        self.reserve()
        self.amend()
        current = self.amend('y', qty=1, expiry=40, version=2)
        self.assertEqual(self.amend(now=100), current)
        self.assertEqual(self.service.available('tea'), 4)
        self.assertEqual(len(self.kinds('a')), 3)
        for kwargs in ({'qty': 4}, {'expiry': 31}, {'version': 2}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Conflict):
                self.amend(**kwargs)

    def test_original_reserve_identity_does_not_follow_amendments(self):
        self.reserve()
        current = self.amend()
        self.assertEqual(self.reserve(now=100), current)
        with self.assertRaises(Conflict):
            self.service.reserve('a', 'tea', 3, 30, 10)
        self.assertEqual(len(self.kinds('a')), 2)

    def test_validation_replay_and_unknown_key_order(self):
        self.reserve()
        cases = ({'change': ''}, {'change': 1}, {'change': None}, {'qty': True},
                 {'qty': 0}, {'qty': -1}, {'qty': 1.5}, {'qty': '3'},
                 {'expiry': True}, {'expiry': 30.5}, {'expiry': '30'},
                 {'version': True}, {'version': False}, {'version': 0},
                 {'version': 1.5}, {'version': '1'}, {'now': False},
                 {'now': 1.5}, {'key': ''})
        for replay in (False, True):
            if replay:
                self.amend()
            before = reservation(self.conn, 'a')
            stock = self.service.available('tea')
            events = self.service.events('a')
            for kwargs in cases:
                with self.subTest(replay=replay, kwargs=kwargs):
                    with self.assertRaises(ValueError) as raised:
                        self.amend(**kwargs)
                    self.assertIs(type(raised.exception), ValueError)
                    self.assertEqual(reservation(self.conn, 'a'), before)
                    self.assertEqual(self.service.available('tea'), stock)
                    self.assertEqual(self.service.events('a'), events)
        with self.assertRaises(ValueError) as raised:
            self.amend(key='missing', qty=True)
        self.assertIs(type(raised.exception), ValueError)
        with self.assertRaises(KeyError):
            self.amend(key='missing')
        self.assertEqual(self.service.available('tea'), 2)
        self.assertEqual(len(self.kinds('a')), 2)

    def test_failed_amendments_do_not_consume_identity(self):
        self.reserve()
        for kwargs, error in [({'qty': 6}, Unavailable), ({'version': 2}, Conflict),
                              ({'expiry': 10}, ValueError)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(error):
                self.amend(**kwargs)
            self.assertEqual(reservation(self.conn, 'a')['version'], 1)
            self.assertEqual(self.service.available('tea'), 3)
            self.assertEqual(self.kinds('a'), ['reserved'])
        self.assertEqual(self.amend()['version'], 2)

    def test_terminal_replay_and_new_command_conflict(self):
        self.reserve()
        self.amend()
        terminal = self.service.cancel('a')
        self.assertEqual(terminal['version'], 3)
        self.assertEqual(self.amend(now=100), terminal)
        with self.assertRaises(Conflict):
            self.amend('new', version=3)
        self.assertEqual(self.service.cancel('a'), terminal)
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended', 'cancelled'])

    def test_expired_replay_and_new_command_conflict(self):
        self.reserve()
        self.amend()
        self.assertEqual(self.service.expire(30), 1)
        item = self.amend(now=100)
        self.assertEqual((item['status'], item['version']), ('expired', 3))
        with self.assertRaises(Conflict):
            self.amend('new', version=3)
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended', 'expired'])

    def test_changed_expiry_boundaries_and_overdue_extension(self):
        self.reserve()
        self.amend(now=25)  # original expiry passed, worker has not run
        self.assertEqual(self.service.expire(20), 0)
        self.amend('shorter', qty=1, expiry=28, version=2, now=25)
        self.assertEqual(self.service.expire(27), 0)
        self.assertEqual(self.service.expire(28), 1)
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(reservation(self.conn, 'a')['version'], 4)

    def test_event_failure_rolls_back_every_amendment_effect(self):
        before = self.reserve()
        self.reject_events('amended')
        with self.assertRaises(sqlite3.IntegrityError):
            self.amend()
        self.assertEqual(self.service.available('tea'), 3)
        self.assertEqual(reservation(self.conn, 'a'), before)
        self.assertEqual(self.kinds('a'), ['reserved'])
        self.conn.execute('DROP TRIGGER reject_event')
        self.assertEqual(self.amend(), {'key': 'a', 'sku': 'tea', 'qty': 3,
                                       'expires_at': 30, 'status': 'active', 'version': 2})
        self.assertEqual(self.service.available('tea'), 2)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended'])
        self.assertEqual(self.amend()['version'], 2)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended'])

    def test_persistence_and_per_reservation_change_namespace(self):
        self.reserve()
        self.reserve('b', qty=1)
        self.amend(qty=2)
        self.amend(key='b', qty=1)
        self.conn.close()
        self.conn = connect(self.path)
        self.addCleanup(self.conn.close)
        self.service = Service(self.conn)
        self.assertEqual(self.reserve(now=100)['version'], 2)
        self.assertEqual(self.amend(qty=2, now=100)['version'], 2)
        self.assertEqual(self.amend(key='b', qty=1, now=100)['version'], 2)
        with self.assertRaises(Conflict):
            self.amend(qty=3)
        self.assertEqual(self.service.available('tea'), 2)

    def test_competing_edits_at_one_version_have_one_winner(self):
        self.reserve()
        outcomes = self.parallel(
            lambda s: s.amend('a', 'x', 3, 30, 1, 10),
            lambda s: s.amend('a', 'y', 1, 40, 1, 10))
        self.assertEqual(sorted(kind for kind, _ in outcomes), ['conflict', 'ok'])
        item = reservation(self.conn, 'a')
        self.assertEqual(item['version'], 2)
        self.assertEqual(self.service.available('tea') + item['qty'], 5)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended'])

    def test_identical_concurrent_amendments_apply_once(self):
        self.reserve()
        outcomes = self.parallel(*[lambda s: s.amend('a', 'x', 3, 30, 1, 10)] * 4)
        self.assertTrue(all(kind == 'ok' for kind, _ in outcomes))
        self.assertTrue(all(item == outcomes[0][1] for _, item in outcomes))
        self.assertEqual(self.service.available('tea'), 2)
        self.assertEqual(self.kinds('a'), ['reserved', 'amended'])

    def test_amendment_racing_cancel_has_legal_serial_outcome(self):
        self.reserve()
        outcomes = self.parallel(lambda s: s.amend('a', 'x', 3, 30, 1, 10),
                                 lambda s: s.cancel('a'))
        self.assertEqual(outcomes[1][0], 'ok')
        item = reservation(self.conn, 'a')
        self.assertEqual(item['status'], 'cancelled')
        amended = outcomes[0][0] == 'ok'
        self.assertEqual(item['version'], 3 if amended else 2)
        self.assertEqual(self.kinds('a'), ['reserved'] + (['amended'] if amended else []) + ['cancelled'])
        self.assertEqual(self.service.available('tea'), 5)

    def test_amendment_racing_expiry_has_legal_serial_outcome(self):
        self.reserve()
        outcomes = self.parallel(lambda s: s.amend('a', 'x', 3, 30, 1, 20),
                                 lambda s: s.expire(20))
        item = reservation(self.conn, 'a')
        if outcomes[0][0] == 'ok':
            self.assertEqual((item['status'], item['version']), ('active', 2))
            self.assertEqual(outcomes[1], ('ok', 0))
            self.assertEqual(self.service.available('tea'), 2)
            self.assertEqual(self.kinds('a'), ['reserved', 'amended'])
        else:
            self.assertEqual((item['status'], item['version']), ('expired', 2))
            self.assertEqual(outcomes[1], ('ok', 1))
            self.assertEqual(self.service.available('tea'), 5)
            self.assertEqual(self.kinds('a'), ['reserved', 'expired'])

    def test_cancel_racing_expiry_restores_once(self):
        self.reserve()
        self.parallel(lambda s: s.cancel('a'), lambda s: s.expire(20))
        item = reservation(self.conn, 'a')
        self.assertIn(item['status'], ('cancelled', 'expired'))
        self.assertEqual(item['version'], 2)
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(self.kinds('a'), ['reserved', item['status']])

    def test_competing_expiry_workers_restore_once(self):
        self.reserve()
        outcomes = self.parallel(*[lambda s: s.expire(20)] * 4)
        self.assertEqual(sum(count for _, count in outcomes), 1)
        self.assertEqual(self.service.available('tea'), 5)
        self.assertEqual(reservation(self.conn, 'a')['version'], 2)
        self.assertEqual(self.kinds('a'), ['reserved', 'expired'])
