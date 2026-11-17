import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from inventory import Conflict, Service
from inventory.storage import connect, seed
from inventory.projection import Gap, Projection, connect_projection


def digest(items):
    text = json.dumps(items, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def collect(page, limit=1):
    after = None
    items = []
    while True:
        result = page(after=after, limit=limit)
        items.extend(result['items'])
        after = result['next']
        if after is None:
            return items


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_path = self.root / 'source.sqlite'
        self.projection_path = self.root / 'projection.sqlite'
        self.source_conn = connect(self.source_path)
        self.addCleanup(self.source_conn.close)
        self.project_conn = connect_projection(self.projection_path)
        self.addCleanup(self.project_conn.close)
        self.source = Service(self.source_conn)
        self.projection = Projection(self.project_conn)
        seed(self.source_conn, 'tea', 12)

    def reopen_source(self):
        self.source_conn.close()
        self.source_conn = connect(self.source_path)
        self.addCleanup(self.source_conn.close)
        self.source = Service(self.source_conn)

    def reopen_projection(self, **kwargs):
        self.project_conn.close()
        self.project_conn = connect_projection(self.projection_path)
        self.addCleanup(self.project_conn.close)
        self.projection = Projection(self.project_conn, **kwargs)

    def test_online_rebuild_recovers_lost_ack_and_post_fence_delivery(self):
        self.source.reserve('a', 'tea', 2, 20, 10)
        self.source.reserve('c', 'tea', 1, 20, 10)
        prior = []

        def deliver_then_drop_ack(event):
            prior.append(event)
            self.assertTrue(self.projection.apply(event))
            raise TimeoutError('delivered, response lost')

        with self.assertRaises(TimeoutError):
            self.source.dispatch(deliver_then_drop_ack)
        stale = {'key': 'ghost', 'sku': 'tea', 'qty': 1, 'expires_at': 50,
                 'status': 'cancelled', 'version': 2}
        self.projection.bootstrap(stale)
        old_view = self.projection.view()
        # The caller has stopped starting callbacks and drained the failed one.
        # Source writes remain enabled across the brief routing barrier.
        manifest = self.source.begin_rebuild('r1')
        self.source.amend('a', 'x', 3, 30, 1, 10)
        self.assertTrue(self.projection.begin_rebuild(manifest))
        self.assertFalse(self.projection.begin_rebuild(manifest))
        with self.assertRaises(Conflict):
            self.projection.bootstrap(stale)
        self.assertEqual(self.projection.view(), old_view)
        seen_before_fence = collect(lambda after=None, limit=1: self.source.seen_page('r1', after, limit))
        authoritative_seen = {event['id']: event for event in seen_before_fence}
        sent = []
        lost = []
        fence = None

        def durable_route(event):
            if event['id'] <= manifest['watermark']:
                if authoritative_seen.get(event['id']) != event:
                    raise Conflict('unknown or changed pre-snapshot identity')
                self.projection.stage_seen('r1', event)
            else:
                self.projection.stage_event('r1', event)
            sent.append(event)
            if fence is not None and event['id'] > fence['through'] and not lost:
                lost.append(event)
                raise TimeoutError('ACK lost after durable staging')

        # The durable router is now installed and callbacks may resume. In this
        # synchronous run its first callback is invoked below, after F.
        page = self.source.snapshot_page('r1', limit=1)
        self.assertEqual([x['key'] for x in page['items']], ['a'])
        self.assertEqual(page['next'], 'a')

        # These are real writes between pages, not updates to the captured page.
        self.source.reserve('b', 'tea', 1, 30, 10)
        fence = self.source.fence_rebuild('r1')
        post_fence = self.source.cancel('a')
        self.assertEqual(post_fence['version'], 3)
        self.assertEqual(self.source.begin_rebuild('r1'), manifest)
        self.assertEqual(self.source.fence_rebuild('r1'), fence)

        self.reopen_source()
        self.reopen_projection()
        self.assertEqual(self.source.begin_rebuild('r1'), manifest)
        self.assertEqual(self.source.fence_rebuild('r1'), fence)
        captured = page['items'] + collect(
            lambda after=None, limit=1: self.source.snapshot_page('r1',
                                                                   after=page['next'] if after is None else after,
                                                                   limit=limit))
        self.assertEqual([item['key'] for item in captured], ['a', 'c'])
        self.assertEqual((manifest['count'], manifest['digest']), (2, digest(captured)))
        seen = collect(lambda after=None, limit=1: self.source.seen_page('r1', after, limit))
        self.assertEqual(seen, seen_before_fence)
        fenced = collect(lambda after=None, limit=1: self.source.rebuild_events('r1', after, limit))
        self.assertEqual((manifest['seen_count'], manifest['seen_digest']), (2, digest(seen)))
        self.assertEqual(fence['event_ids'], [event['id'] for event in fenced])
        self.assertEqual(fence['digest'], digest(fenced))

        # Source delivery is acknowledged only after staging durably. The first
        # delivery was already seen before W and must route through stage_seen.
        # The final callback stages post-F data, then loses the acknowledgement.
        with self.assertRaisesRegex(TimeoutError, 'ACK lost'):
            self.source.dispatch(durable_route)
        self.assertEqual(sent[0], prior[0])  # pre-W lost ACK was redelivered
        pending = lost[0]
        self.reopen_source()
        self.reopen_projection()
        self.assertEqual(self.source.dispatch(durable_route), 1)
        self.assertEqual(sent[-1], pending)  # staged duplicate survived restart
        for event in reversed(fenced):
            self.assertFalse(self.projection.stage_event('r1', event))
        for item in captured:
            self.assertTrue(self.projection.stage_snapshot('r1', item))
            self.assertFalse(self.projection.stage_snapshot('r1', item))
        for event in seen:
            self.assertFalse(self.projection.stage_seen('r1', event))
        self.assertEqual(self.projection.view(), old_view)
        with self.assertRaises(Conflict):
            self.projection.apply(pending)
        with self.assertRaises(Conflict):
            self.projection.stage_snapshot('r1', {**captured[0], 'qty': 9})

        calls = []

        def interrupt(conn, token):
            calls.append(token)
            raise RuntimeError('reporting process stopped before commit')

        self.reopen_projection(cutover_hook=interrupt)
        with self.assertRaisesRegex(RuntimeError, 'stopped before commit'):
            self.projection.cutover('r1', fence)
        self.assertEqual(calls, ['r1'])
        self.assertEqual(self.projection.view(), old_view)
        self.reopen_projection()
        self.assertEqual(self.projection.view(), old_view)
        self.assertTrue(self.projection.cutover('r1', fence))
        new_view = self.projection.view()
        self.assertEqual([x['key'] for x in new_view], ['a', 'b', 'c'])
        self.assertEqual(next(x for x in new_view if x['key'] == 'a')['version'], 2)
        self.assertEqual(self.projection.pending('r1'), [pending])
        self.assertFalse(self.projection.apply(prior[0]))
        with self.assertRaises(Conflict):
            self.projection.apply({**prior[0], 'qty': 99})
        with self.assertRaises(Conflict):
            self.projection.ack_pending('r1', pending['id'])
        self.assertTrue(self.projection.apply(pending))
        self.reopen_projection()  # crash after apply before acknowledging staging
        self.assertFalse(self.projection.apply(pending))
        self.assertTrue(self.projection.ack_pending('r1', pending['id']))
        self.assertFalse(self.projection.ack_pending('r1', pending['id']))
        self.assertFalse(self.projection.stage_event('r1', pending))
        with self.assertRaises(Conflict):
            self.projection.stage_event('r1', {**pending, 'qty': 9})
        self.assertEqual(self.projection.pending('r1'), [])
        self.assertFalse(self.projection.cutover('r1', fence))
        self.assertEqual(self.projection.get('a')['status'], 'cancelled')

    def test_missing_or_modified_capture_is_not_cut_over(self):
        self.source.reserve('a', 'tea', 2, 20, 10)
        manifest = self.source.begin_rebuild('missing')
        self.source.amend('a', 'x', 3, 30, 1, 10)
        fence = self.source.fence_rebuild('missing')
        self.projection.begin_rebuild(manifest)
        snapshots = collect(lambda after=None, limit=1: self.source.snapshot_page('missing', after, limit))
        seen = collect(lambda after=None, limit=1: self.source.seen_page('missing', after, limit))
        events = collect(lambda after=None, limit=1: self.source.rebuild_events('missing', after, limit))
        self.projection.stage_snapshot('missing', snapshots[0])
        self.projection.stage_event('missing', events[0])
        old_view = self.projection.view()
        with self.assertRaises(Conflict):
            self.projection.cutover('missing', fence)  # pre-W identity omitted
        self.assertEqual(self.projection.view(), old_view)
        self.projection.stage_seen('missing', seen[0])
        with self.assertRaises(Conflict):
            self.projection.stage_seen('missing', {**seen[0], 'qty': 100})
        with self.assertRaises(Conflict):
            self.projection.cutover('missing', {**fence, 'digest': '0' * 64})
        self.assertEqual(self.projection.view(), old_view)
        self.assertTrue(self.projection.cutover('missing', fence))
        self.assertEqual(self.projection.get('a')['version'], 2)

    def test_missing_fenced_event_is_conflict_before_sequence_gap(self):
        self.source.reserve('a', 'tea', 2, 20, 10)
        manifest = self.source.begin_rebuild('gap-order')
        self.source.amend('a', 'x', 3, 30, 1, 10)
        self.source.amend('a', 'y', 2, 40, 2, 10)
        fence = self.source.fence_rebuild('gap-order')
        self.projection.begin_rebuild(manifest)
        self.projection.stage_snapshot('gap-order', self.source.snapshot_page('gap-order')['items'][0])
        self.projection.stage_seen('gap-order', self.source.seen_page('gap-order')['items'][0])
        first, second = self.source.rebuild_events('gap-order')['items']
        self.projection.stage_event('gap-order', second)
        with self.assertRaises(Conflict):
            self.projection.cutover('gap-order', fence)
        self.assertEqual(self.projection.view(), [])
        self.projection.stage_event('gap-order', first)
        self.assertTrue(self.projection.cutover('gap-order', fence))
        self.assertEqual(self.projection.get('a')['version'], 3)

    def test_empty_capture_reopen_and_validated_pages(self):
        manifest = self.source.begin_rebuild('empty')
        self.assertEqual(manifest['digest'], digest([]))
        self.assertEqual(manifest['seen_digest'], digest([]))
        self.assertEqual(self.source.snapshot_page('empty', limit=1), {'items': [], 'next': None})
        self.assertEqual(self.source.seen_page('empty', limit=1), {'items': [], 'next': None})
        with self.assertRaises(Conflict):
            self.source.rebuild_events('empty')
        fence = self.source.fence_rebuild('empty')
        self.assertEqual(fence['event_ids'], [])
        self.assertEqual(fence['digest'], digest([]))
        self.assertTrue(self.projection.begin_rebuild(manifest))
        with self.assertRaises(ValueError):
            self.projection.cutover('unknown', {**fence, 'digest': 'not-a-digest'})
        with self.assertRaises(KeyError):
            self.projection.cutover('unknown', fence)
        with self.assertRaises(Conflict):
            self.projection.cutover('empty', {**fence, 'token': 'different'})
        self.assertTrue(self.projection.cutover('empty', fence))
        self.reopen_projection()
        self.assertFalse(self.projection.cutover('empty', fence))
        self.assertEqual(self.projection.view(), [])
        for limit in (0, -1, True, 2**63, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.source.snapshot_page('empty', limit=limit)
        with self.assertRaises(KeyError):
            self.source.snapshot_page('unknown')

    def test_malformed_delivery_and_bootstrap_are_validated_before_active_rebuild(self):
        manifest = self.source.begin_rebuild('validation-order')
        self.projection.begin_rebuild(manifest)
        snapshot = {'key': 'a', 'sku': 'tea', 'qty': 1, 'expires_at': 20,
                    'status': 'active', 'version': 1}
        envelope = {**snapshot, 'id': 1, 'kind': 'reserved'}
        for action in (lambda: self.projection.bootstrap(None),
                       lambda: self.projection.bootstrap({**snapshot, 'qty': True}),
                       lambda: self.projection.apply(None),
                       lambda: self.projection.apply({**envelope, 'id': True})):
            with self.subTest(action=action):
                with self.assertRaises(ValueError) as caught:
                    action()
                self.assertIs(type(caught.exception), ValueError)
        with self.assertRaises(Conflict):
            self.projection.bootstrap(snapshot)
        with self.assertRaises(Conflict):
            self.projection.apply(envelope)
        self.assertEqual(self.projection.view(), [])

    def test_operator_repairs_poisoned_staging_without_losing_evidence(self):
        self.source.reserve('a', 'tea', 2, 20, 10)
        manifest = self.source.begin_rebuild('repair')
        self.source.amend('a', 'x', 3, 30, 1, 10)
        fence = self.source.fence_rebuild('repair')
        snapshot = self.source.snapshot_page('repair')['items'][0]
        seen = self.source.seen_page('repair')['items'][0]
        event = self.source.rebuild_events('repair')['items'][0]
        self.projection.begin_rebuild(manifest)
        poisoned_snapshot = {**snapshot, 'qty': 9}
        poisoned_event = {**event, 'qty': 4}
        extra = {**event, 'id': fence['through'] + 1, 'version': 3}
        self.projection.stage_snapshot('repair', poisoned_snapshot)
        self.projection.stage_seen('repair', seen)
        self.projection.stage_event('repair', poisoned_event)
        self.projection.stage_event('repair', extra)
        with self.assertRaises(Conflict):
            self.projection.cutover('repair', fence)
        self.assertEqual(self.projection.view(), [])
        with self.assertRaises(Conflict):
            self.projection.repair_staged('repair', 'snapshot',
                                          {**poisoned_snapshot, 'qty': 10}, snapshot)
        with self.assertRaises(Conflict):
            self.projection.repair_staged('repair', 'event', poisoned_event,
                                          {**event, 'id': event['id'] + 1})
        self.assertEqual(self.projection.quarantined('repair'), [])
        self.assertTrue(self.projection.repair_staged('repair', 'snapshot',
                                                     poisoned_snapshot, snapshot))
        self.assertTrue(self.projection.repair_staged('repair', 'event', poisoned_event, event))
        self.assertTrue(self.projection.repair_staged('repair', 'event', extra))
        expected_audit = [
            {'category': 'snapshot', 'original': poisoned_snapshot, 'replacement': snapshot},
            {'category': 'event', 'original': poisoned_event, 'replacement': event},
            {'category': 'event', 'original': extra, 'replacement': None},
        ]
        self.reopen_projection()
        self.assertEqual(self.projection.quarantined('repair'), expected_audit)
        self.assertTrue(self.projection.cutover('repair', fence))
        self.reopen_projection()
        self.assertEqual(self.projection.get('a')['version'], 2)
        self.assertEqual(self.projection.quarantined('repair'), expected_audit)
        self.assertEqual(self.projection.pending('repair'), [])
        with self.assertRaises(Conflict):
            self.projection.repair_staged('repair', 'event', event)
        with self.assertRaises(Conflict):
            self.projection.repair_staged('repair', 'event',
                                          {**event, 'id': event['id'] + 100})

    def test_operator_repairs_poisoned_manifest_without_removing_staged_items(self):
        self.source.reserve('a', 'tea', 2, 20, 10)
        manifest = self.source.begin_rebuild('manifest-repair')
        fence = self.source.fence_rebuild('manifest-repair')
        snapshot = self.source.snapshot_page('manifest-repair')['items'][0]
        seen = self.source.seen_page('manifest-repair')['items'][0]
        poisoned = {**manifest, 'digest': '0' * 64}
        self.projection.begin_rebuild(poisoned)
        self.projection.stage_snapshot('manifest-repair', snapshot)
        self.projection.stage_seen('manifest-repair', seen)
        with self.assertRaises(Conflict):
            self.projection.cutover('manifest-repair', fence)
        with self.assertRaises(Conflict):
            self.projection.repair_manifest('manifest-repair',
                                            {**poisoned, 'count': 2}, manifest)
        with self.assertRaises(Conflict):
            self.projection.repair_manifest('manifest-repair', poisoned,
                                            {**manifest, 'token': 'other'})
        with self.assertRaises(Conflict):
            self.projection.repair_manifest('manifest-repair', poisoned,
                                            {**manifest, 'watermark': 0})
        self.assertEqual(self.projection.quarantined('manifest-repair'), [])
        self.assertTrue(self.projection.repair_manifest('manifest-repair', poisoned, manifest))
        self.assertFalse(self.projection.repair_manifest('manifest-repair', manifest, manifest))
        audit = [{'category': 'manifest', 'original': poisoned, 'replacement': manifest}]
        self.reopen_projection()
        self.assertEqual(self.projection.quarantined('manifest-repair'), audit)
        self.assertTrue(self.projection.cutover('manifest-repair', fence))
        self.assertFalse(self.projection.apply(seen))
        self.assertEqual(self.projection.get('a')['qty'], 2)
        self.assertEqual(self.projection.quarantined('manifest-repair'), audit)
        with self.assertRaises(Conflict):
            self.projection.repair_manifest('manifest-repair', manifest, manifest)
