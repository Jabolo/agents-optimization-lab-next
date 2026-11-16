# Task 1 — stock movements

Run `python3 -m unittest discover -s tests -v` from this folder. Make the supplied
tests green by repairing `stock.py`. Then examine your interaction using
`../RETRO.md` and try one workflow improvement. No other task is needed to start.

`balances(events)` accepts an iterable of dictionaries with `id`, `sku`, `delta`.
Return a dictionary of totals by SKU, including zero and negative totals.

- IDs/SKUs must be nonempty strings; delta must be an integer, excluding booleans.
- Every unique event is counted once. An exact retry with the same ID and payload
  is ignored. The same ID with different SKU or delta raises `ValueError`.
- Malformed events raise `ValueError`; do not mutate input. Ignore extra fields.
- Empty input returns `{}`. Accept a one-pass iterable; do not require a list.

This is a small task for a demonstration or practice. The presenter may show a
solution. Record that exposure; a replay is not an independent performance trial.
