"""Reproduce a lost notification locally. Only temporary files are used."""
from pathlib import Path
import tempfile

from inventory import Service
from inventory.storage import connect, seed


def main():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'source.sqlite'
        conn = connect(path)
        try:
            seed(conn, 'tea', 5)
            service = Service(conn)
            item = service.reserve('order-42', 'tea', 2, 20, 10)
            delivered = []

            def deliver_then_drop_ack(envelope):
                delivered.append(envelope)
                raise TimeoutError('connection dropped after delivery')

            try:
                service.dispatch(deliver_then_drop_ack)
            except TimeoutError as error:
                print(f'Publisher: {error}')
            print(f"Source reservation: key={item['key']}, stock remaining={service.available('tea')}")
            print(f'Deliveries before restart: {len(delivered)}')
        finally:
            conn.close()
        conn = connect(path)
        try:
            service = Service(conn)
            retry = []
            acknowledged = service.dispatch(retry.append)
            print(f'Retry after restart: {len(retry)} delivery, {acknowledged} acknowledged')
            if len(delivered) == 1 and len(retry) == 1 and acknowledged == 1 and delivered[0] == retry[0]:
                print('Expected duplicate retry preserved the original notification.')
                return 0
            print('INCIDENT: the committed notification could not be safely retried.')
            return 1
        finally:
            conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
