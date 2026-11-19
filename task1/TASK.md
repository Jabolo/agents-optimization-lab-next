# Task 1 — stock movements

From the repository root, run your first red check right away (Windows: `py -3`):

```sh
python3 check.py task1 --record runs/initial/task1-tests.json
```

Or run `python3 -m unittest discover -s tests -v` inside this `task1/` folder (save manual logs to `../runs/initial/`, using `2>&1` on macOS/Linux or `*>&1 | Tee-Object` in Windows PowerShell since `unittest` writes to `stderr`). Jot a 3-line baseline note in `runs/RESULT.md` using [RESULT-TEMPLATE.md](../RESULT-TEMPLATE.md), then make the supplied tests green by repairing `stock.py` while keeping supplied tests intact. Afterward, examine your interaction in a fresh chat using [RETRO.md](../RETRO.md) and test one workflow change in [EXPERIMENT.md](../EXPERIMENT.md). No other task is needed to start.

`balances(events)` accepts an iterable of dictionaries with `id`, `sku`, `delta`.
Return a dictionary of totals by SKU, including zero and negative totals.

- IDs/SKUs must be nonempty strings; delta must be an integer, excluding booleans.
- Every unique event is counted once. An exact retry with the same ID and payload
  is ignored. The same ID with different SKU or delta raises `ValueError`.
- Malformed events raise `ValueError`; do not mutate input. Ignore extra fields.
- Empty input returns `{}`. Accept a one-pass iterable; do not require a list.

This is a small task for a demonstration or practice. The presenter may show a
solution. Record that exposure; a replay is not an independent performance trial.
If your agent finishes in under a minute, check uncovered edges (`delta=False`,
non-adjacent retry) or try [Task 2](../task2/TASK.md) for deeper workflow friction.
