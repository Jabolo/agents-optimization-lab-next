# The Agents Optimization Lab

**Use your coding agent on a real task. Examine how you worked, then try one change to your workflow.**

Work individually at your own pace using your usual agent, model, skills, tools, and delegation—nothing extra is required. The code gives you grounded evidence so you can leave with a clear choice: what to keep, change, or test next.

## Your 30-minute session and vibe lounge

In the room, choose one task, run its starting check, work normally with your
agent, and notice one thing about your workflow. An unfinished task is fine.
During the closing, save your observation, evidence location, and next step in
`runs/RESULT.md` or a short note; keep your working copy and any logs.

In the **vibe lounge**, open that same copy and continue where you stopped. Give
a fresh chat your interaction and evidence using [RETRO.md](RETRO.md), choose one
small change in [EXPERIMENT.md](EXPERIMENT.md), try it, and record what happened
or what remains unknown. If you already reached the retro in the room, continue
your experiment instead. There is no need to finish both tasks or start over.
You can work through the whole lab at your own pace even without the room session.

## Prerequisites

- Your existing authenticated coding agent
- Python 3.11+ (no extra packages, server, or new account needed):

```sh
python3 --version   # Windows PowerShell: py -3 --version
```

## Choose your task

- **[Task 1 — stock movements](task1/TASK.md):** ~5-minute warm-up or demo (`stock.py`).
- **[Task 2 — recovery incident](task2/TASK.md):** deeper service incident (independent of Task 1, best for realistic workflow friction). In the short room session, start with `incident.py` and one bounded slice. Debugging itself is useful material for [RETRO.md](RETRO.md).

## Start

1. **Get the repo** and open its **root** in your coding agent:

   ```sh
   git clone https://github.com/Jabolo/agents-optimization-lab-next.git
   cd agents-optimization-lab-next
   ```

   *Using GitHub Download ZIP?* It extracts to `agents-optimization-lab-next-main/` with no `.git/` folder—keep a second fresh extracted copy if you plan a Repeat later, and skip `git` diff commands.

2. **Run your first red check right away** (from the repository root; on Windows use `py -3`):

   - **Task 1:**

     ```sh
     python3 check.py task1 --record runs/initial/task1-tests.json
     ```

   - **Task 2** (run separately—`incident.py` is expected to exit `1`):

     ```sh
     python3 task2/incident.py
     python3 check.py task2 -p test_recovery.py -k lost_ack --record runs/initial/lost-ack.json
     ```

   `check.py` prints a 1-line `Summary` even without `--record`, and `--record` saves structured JSON. To also capture console output and exit codes (needed for `incident.py` or manual `unittest` runs—note `unittest` writes 100% of its output to `stderr`, so `2>&1` is mandatory, and `>` overwrites existing files, so use unique filenames):

   - **macOS / Linux:**

     ```sh
     mkdir -p runs/initial
     python3 task2/incident.py > runs/initial/incident.log 2>&1
     printf '%s\n' "$?" > runs/initial/incident.exit
     ```

   - **Windows PowerShell:**

     ```powershell
     New-Item -ItemType Directory -Force runs/initial | Out-Null
     py -3 task2/incident.py *>&1 | Tee-Object -FilePath runs/initial/incident.log
     $LASTEXITCODE | Set-Content runs/initial/incident.exit
     ```

   Failing assertions and starter exceptions are normal; missing Python, import errors, or zero discovered tests indicate a setup issue.

3. **Jot a short baseline note** in `runs/RESULT.md` using [RESULT-TEMPLATE.md](RESULT-TEMPLATE.md): task and commit/folder, your usual approach, and one expectation (`unknown` is fine). Note your start time if you want to measure elapsed time. Create `runs/initial/` and `runs/changed/` if not already created.

   - **Adapt vs Repeat:** **Adapt** adjusts your current attempt or its next review/check (a practical starting point for the short session or sandboxed workspaces); **Repeat** retries from an untouched sibling copy of the whole repo in a fresh chat.
   - Make an untouched sibling copy now **only** if you used Download ZIP or plan a Repeat; skip this gracefully if your agent sandbox blocks writing outside the repo.

4. **Work normally with your agent.** Point your agent at [AGENTS.md](AGENTS.md) (helpful for tools that do not auto-load it) and paste a starter prompt:

   - **Task 2:**

     > Read `AGENTS.md` and `task2/TASK.md` (refer to `task2/CONTRACT.md` as needed). Start from my baseline in `runs/RESULT.md` and the initial checks in `runs/initial/` (run `task2/incident.py` and the `lost_ack` check first if not run yet). Help me investigate and fix the incident or a bounded slice using my normal workflow. Keep supplied tests intact, show actual outputs, and save this attempt's checks in `runs/initial/`.

   - **Task 1:**

     > Read `AGENTS.md` and `task1/TASK.md`. Start from my baseline note in `runs/RESULT.md` and the initial output in `runs/initial/` (run the initial `task1` check first if not run yet). Help me inspect the failures, repair `task1/stock.py`, and verify edge cases using my normal workflow. Keep supplied tests intact, show actual outputs and exit codes, and save this attempt's checks in `runs/initial/`.

5. **Retro, one experiment, and decision.** When ready, including if you are stuck, open a **fresh chat** (it cannot see prior history automatically) with [RETRO.md](RETRO.md), pick **one** change in [EXPERIMENT.md](EXPERIMENT.md) (`Adapt` or `Repeat`), save new evidence in `runs/changed/`, and record your choice in `runs/RESULT.md`. Start this in the room if time allows, or continue in the vibe lounge.

## What counts as progress?

- **Incident or slice checked:** Task 2 starts with one delivery and zero retries; a repaired incident retries once and acknowledges once (an in-memory fake, not durable reporting). Full requirements live in [task2/CONTRACT.md](task2/CONTRACT.md).
- **Optional post-green check:** Challenge a claim even while other tests stay red (see [task2/TASK.md#challenge-a-result](task2/TASK.md#challenge-a-result)), or pick another experiment in [EXPERIMENT.md](EXPERIMENT.md).
- **Workflow learned:** Leave with one concrete observation, one tested change (or intentional keep), and supporting output—even if tests are still red. If you saw a Task 1 demo, label a replay as prior exposure; Task 1 and Task 2 timings are not comparable.

## If you get stuck

- Confirm `python3 --version` (Windows: `py -3 --version`) is 3.11+ and check your working folder (`repo root` for `check.py`; `task1/` or `task2/` for direct `unittest` runs).
- **Need a fresh start?** Leave your current copy and notes intact; clone the repo into a new folder or extract the same ZIP again into a separate folder. Git reset and clean commands can delete work, including newly created solution files.
- Keep partial outputs and unsuccessful experiments—they are useful evidence.

Optional closing Q&A template: **I changed ___; I observed ___; I would use it again when ___; I still don't know ___.**
