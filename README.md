# The Agents Optimization Lab

**Use your coding agent on a real task. Examine how you worked, then try one change to your workflow.**

You can use your usual agent, model, skills, tools, and delegation. Work at your own pace. The code gives you evidence; your goal is to leave with a choice you can explain: what to keep, change, or investigate next.

You need Python 3.11+ and your existing authenticated agent. No packages or server are required. On Windows, use a verified `py -3` in place of `python3`.

## Start

1. **Choose a task.** [Task 1](task1/TASK.md) is the small demo. [Task 2](task2/TASK.md) is a deeper recovery incident; it is independent of task 1.
2. **Before editing**, note the start time, your usual approach, and one expectation. Ask your agent to preserve an untouched copy of the **whole repository** in a separate sibling folder, outside this repository, without overwriting anything. Make `runs/initial/` and `runs/changed/` for your evidence. Copy [RESULT-TEMPLATE.md](RESULT-TEMPLATE.md) to `runs/RESULT.md`, or use a short note in your own format. Unknown values are fine.
3. **Observe the starting state.** For task 1, run `python3 -m unittest discover -s tests -v` in `task1`. For task 2, run `python3 incident.py` in `task2`, then the focused check shown in [its task card](task2/TASK.md). Save the actual output. Failing assertions and implementation exceptions are expected in the starter; missing Python, import errors, and undiscovered tests are setup problems.
4. **Work normally with your agent.** Inspect the result and run checks. Then use [RETRO.md](RETRO.md) in a fresh chat, choose one workflow change, and try it using [EXPERIMENT.md](EXPERIMENT.md).
5. **Record your decision.** What did you observe? What did you change? What will you keep, change, or investigate next, and what evidence supports that choice?

To start task 2, point your agent at this repository and paste:

> Help me investigate task 2 and improve how I work with you. First ask for my usual approach and expectation, or let me mark them unknown. Preserve a clean copy of the whole repository in a separate sibling folder without overwriting anything, and create `runs/initial/` and `runs/changed/`. From `task2`, run `python3 incident.py` and the focused lost-ack test in TASK.md; save their actual output. Explain what happened briefly, then help me solve it normally. Keep supplied tests intact. Help me preserve our interaction and check results for a fresh-chat retro. My observation and final choice are mine.

For task 1, paste:

> Help me investigate task 1 and improve how I work with you. First ask for my usual approach and expectation, or let me mark them unknown. Preserve a clean copy of the whole repository in a separate sibling folder without overwriting anything, and create `runs/initial/` and `runs/changed/`. From `task1`, run `python3 -m unittest discover -s tests -v` and save the actual output. Explain what happened briefly, then help me solve it normally. Keep supplied tests intact. Help me preserve our interaction and check results for a fresh-chat retro. My observation and final choice are mine.

If your agent cannot export a transcript, save a clearly labelled summary, actual commands and outputs, the diff, and copies of relevant untracked files. A new chat does not automatically see the old one.

## What counts as progress?

- **Incident checked:** task 2 starts with one delivery and zero retries. A repaired incident retries the same notification once and acknowledges it once. This local check does not prove durable reporting.
- **Implementation checked:** run the full supplied suite from your selected task and inspect its output. Green tests cover the listed examples, not every possible behavior; task 2's complete [contract](task2/CONTRACT.md) is available from the start.
- **Workflow learned:** record one observation grounded in your interaction, try one change, and state what happened or what remains unknown. You can do this even if the code is unfinished or your current workflow is already useful.

If you saw the task-1 demo, label a replay as prior exposure. Task 1 and task 2 are different problems, so their timings do not measure a workflow improvement. Keep supplied tests intact; add checks when useful.

Optional: from this repository root, `python3 check.py task2 --record runs/initial/tests.json` saves structured full-suite evidence. Choose a new path each time; this measures test execution only, not solving time. The plain unittest command also works.

## If you get stuck

- Check `python3 --version` (Windows: `py -3 --version`) is 3.11 or newer, and run the command in the selected task folder.
- An import error or zero discovered tests suggests the wrong folder or Python setup. Ask your agent to show the current folder and exact error, or ask the presenter.
- Keep your original files and outputs. A partial attempt, failed experiment, or decision to keep your current approach is useful evidence.

At the closing Q&A, sharing is optional: **I changed ___; I observed ___; I would use it again when ___; I still don't know ___.** You can continue later.

Prototype status: participant comprehension, difficulty, and classroom timing have not been human-tested.
