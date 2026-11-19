# Working with a participant

Let the participant drive their normal workflow unless they ask for structure. Do not hide requirements, prescribe coding order, or install frameworks unless asked.

- **Test integrity:** Keep supplied `tests/*.py` files intact; separate added checks are fine.
- **Personal record ownership:** Never fill or overwrite the participant's personal expectations, observations, checkpoints, or decisions in `runs/RESULT.md` unless explicitly asked.
- **Honest evidence:** Show actual commands, raw outputs, and exit codes. Distinguish passing examples from full coverage. Never invent expectations, timings, observations, or costs.
- **Clean checks & shell capture:** From repo root run `python3 check.py <task>` (supports `-p`/`-k` and `--record`, printing a 1-line `Summary`), or `python3 -m unittest discover -s tests -v` inside `task1/` or `task2/` (Windows: `py -3`). Always include `2>&1` on macOS/Linux (`*>&1` in Windows PowerShell) when capturing console output because `unittest` and `check.py` write to `stderr`, and always choose a new `--record` filename per run (`check.py` refuses existing files).
- **Evidence hygiene:** Save initial and experiment outputs separately (`runs/initial/` vs `runs/changed/`) without overwriting. Keep personal records local; never commit them unless asked.
- **Fresh-chat handoff:** A new chat never sees prior history automatically. If the fresh chat can access this workspace, a brief factual summary (`runs/initial/summary.md` or inline) plus `git status --short --ignored` and paths to `runs/initial/` is enough (`git diff` can run on demand). Only if it cannot access the workspace should you export `git diff`, relevant new-file contents, and raw outputs; mark omissions `unknown`.
