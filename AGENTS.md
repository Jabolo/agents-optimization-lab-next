# Working with a participant

Let the participant drive their normal workflow unless they ask for structure. Do not hide requirements, prescribe coding order, or install frameworks unless asked.

- **Test integrity:** Keep supplied `tests/*.py` files intact; separate added checks are fine.
- **Honest evidence:** Show actual commands, raw outputs, and exit codes. Distinguish passing examples from full coverage. Never invent expectations, timings, observations, or costs.
- **Clean checks:** From repo root run `python3 check.py <task>` (supports `-p`/`-k` and `--record`, printing a 1-line `Summary`), or `python3 -m unittest discover -s tests -v` inside `task1/` or `task2/` (Windows: `py -3`).
- **Evidence hygiene:** Save initial and experiment outputs separately (`runs/initial/` vs `runs/changed/`) without overwriting. Keep personal records local; never commit them unless asked.
- **Fresh-chat handoff:** A new chat never sees prior history automatically. Package status, changes from baseline, relevant new files, outputs, and test paths. If it cannot access the workspace, include the contents of relevant files the participant chooses to share; mark omissions unknown.
