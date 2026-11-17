"""Exercise a separate persisted migration and lost-acknowledgement scenario.

Run this after repairing Task 2: ``python3 replay.py``. It uses only temporary
SQLite files, exercises documented Task 2 behavior, and exits nonzero on a
failed invariant. Passing these examples does not prove complete correctness.
"""

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import traceback

from inventory import Service
from inventory.projection import Projection, connect_projection
from inventory.storage import connect


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def create_legacy_fixture(path):
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript('''
            PRAGMA user_version=1;
            CREATE TABLE stock(sku TEXT PRIMARY KEY, available INTEGER NOT NULL);
            CREATE TABLE reservations(key TEXT PRIMARY KEY, sku TEXT NOT NULL,
                qty INTEGER NOT NULL, expires_at INTEGER NOT NULL, status TEXT NOT NULL);
            CREATE TABLE events(id INTEGER PRIMARY KEY, key TEXT NOT NULL, kind TEXT NOT NULL);
            INSERT INTO stock VALUES ('beans', 4), ('mug', 6);
            INSERT INTO reservations VALUES ('legacy-active', 'beans', 2, 50, 'active'),
                                            ('legacy-cancelled', 'mug', 1, 60, 'cancelled');
            INSERT INTO events VALUES (-17, 'legacy-active', 'reserved'),
                                      (-3, 'legacy-cancelled', 'cancelled');
        ''')
        conn.commit()


def replay():
    with tempfile.TemporaryDirectory(prefix='agents-lab-replay-') as folder:
        source_path = Path(folder) / 'source.sqlite'
        projection_path = Path(folder) / 'reporting.sqlite'
        create_legacy_fixture(source_path)

        with closing(connect(source_path)) as source, closing(connect_projection(projection_path)) as reporting:
            service, projection = Service(source), Projection(reporting)
            expect(source.execute('PRAGMA user_version').fetchone()[0] == 2,
                   'legacy database did not migrate to version 2')
            history = [tuple(row) for row in source.execute('SELECT id,key,kind FROM events ORDER BY id')]
            expect(history == [(-17, 'legacy-active', 'reserved'), (-3, 'legacy-cancelled', 'cancelled')],
                   'migration did not preserve historical audit rows')
            for snapshot in service.snapshots():
                projection.bootstrap(snapshot)
            expect(service.dispatch(lambda _: None) == 0,
                   'migration unexpectedly republished historical events')
            service.amend('legacy-active', 'change-1', 3, 80, 1, 10)
            service.reserve('new-order', 'mug', 2, 90, 10)
            expect(service.available('beans') == 3 and service.available('mug') == 4,
                   'new transactions left incorrect available stock')

            first_delivery = []

            def deliver_then_lose_ack(envelope):
                first_delivery.append(dict(envelope))
                expect(projection.apply(envelope) is True,
                       'first notification was not applied to reporting')
                raise TimeoutError('simulated lost acknowledgement after reporting commit')

            try:
                service.dispatch(deliver_then_lose_ack)
            except TimeoutError:
                pass
            else:
                raise AssertionError('publisher exception was not propagated')
            expect(len(first_delivery) == 1, 'lost acknowledgement did not stop the batch')
            first = first_delivery[0]
            expect(first['id'] > 0 and first['id'] not in (-17, -3),
                   'new event did not receive a distinct positive ID')
            expect(first['key'] == 'legacy-active' and first['version'] == 2 and first['kind'] == 'amended',
                   'the first notification did not capture the amendment')
            print('Migrated legacy data; reporting applied an amendment before its acknowledgement was lost.')

        with closing(connect(source_path)) as source, closing(connect_projection(projection_path)) as reporting:
            service, projection = Service(source), Projection(reporting)
            received, applied = [], []

            def deliver(envelope):
                received.append(dict(envelope))
                applied.append(projection.apply(envelope))

            acknowledged = service.dispatch(deliver)
            expect(acknowledged == 2 and len(received) == 2,
                   f'expected two pending deliveries after restart; got {len(received)} / {acknowledged} acknowledged')
            expect(received[0] == first, 'retry did not preserve the original complete notification')
            expect(applied == [False, True],
                   f'expected duplicate then new application; got {applied!r}')
            expect(received[1]['id'] > first['id'] and received[1]['key'] == 'new-order',
                   'second notification did not preserve source transition order')
            expect(service.dispatch(deliver) == 0, 'acknowledged notifications were sent again')
            expect(projection.get('legacy-active') == {
                'key': 'legacy-active', 'sku': 'beans', 'qty': 3, 'expires_at': 80,
                'status': 'active', 'version': 2}, 'reporting state for the amendment is wrong')
            expect(projection.get('legacy-cancelled') == {
                'key': 'legacy-cancelled', 'sku': 'mug', 'qty': 1, 'expires_at': 60,
                'status': 'cancelled', 'version': 1}, 'an unrelated migrated reservation changed')
            expect(projection.get('new-order') == {
                'key': 'new-order', 'sku': 'mug', 'qty': 2, 'expires_at': 90,
                'status': 'active', 'version': 1}, 'reporting state for the new order is wrong')
            expect(service.available('beans') == 3 and service.available('mug') == 4,
                   'available stock changed across reopen or retry')
            expect(service.reserve('legacy-active', 'beans', 2, 50, 100)['version'] == 2,
                   'original request identity did not survive migration and amendment')
            print('PASS: after restart the duplicate had no second effect, the next event applied,')
            print('and migrated records, request identity, stock, and reporting matched this scenario.')
    return 0


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        return replay()
    except Exception as error:
        print(f'REPLAY FAILED: {type(error).__name__}: {error}')
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
