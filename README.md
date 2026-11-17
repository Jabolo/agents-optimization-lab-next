# The Agents Optimization Lab

**Use your coding agent on a real task. Examine how you worked, then try one change to your workflow.**

You can use your usual agent, model, skills, tools, and delegation. Work at your own pace. The code gives you evidence; your goal is to leave with a choice you can explain: what to keep, change, or investigate next.

You need Python 3.11+ and your existing authenticated agent. No packages or server are required. On Windows, use a verified `py -3` in place of `python3`.

## Start

If you are viewing this on GitHub, clone the lab and open the **repository root**
in your coding agent (or give your agent the URL and ask it to do this):

```sh
git clone https://github.com/Jabolo/agents-optimization-lab-next.git
cd agents-optimization-lab-next
```

Already have a copy? Open its root in your agent. Paths such as `runs/` below are
relative to that root; test commands say when to run them inside a task folder.

1. **Choose a task.** [Task 1](task1/TASK.md) is the small demo. [Task 2](task2/TASK.md) is a deeper recovery incident; it is independent of task 1.
2. **Before editing**, note the starting commit or folder, start time, your usual approach, and one expectation. For an optional repeat, ask your agent to preserve an untouched copy of the **whole repository** in a separate sibling folder, outside this repository, without overwriting anything. If that is blocked, note it and continue; you can use the Adapt route later. Make `runs/initial/` and `runs/changed/` for your evidence. Copy [RESULT-TEMPLATE.md](RESULT-TEMPLATE.md) to `runs/RESULT.md`, or use a short note in your own format. Unknown values are fine.
3. **Observe the starting state.** For task 1, run `python3 -m unittest discover -s tests -v` in `task1`. For task 2, run `python3 incident.py` in `task2`, then the focused check shown in [its task card](task2/TASK.md). Save the actual output, including stderr, and the exit status. Run the task-2 commands separately: the expected nonzero incident exit would stop a chain joined by `&&`. Failing assertions and implementation exceptions are expected in the starter; missing Python, import errors, and undiscovered tests are setup problems.
4. **Work normally with your agent.** Inspect the result and run checks. Then use [RETRO.md](RETRO.md) in a fresh chat, choose one workflow change, and try it using [EXPERIMENT.md](EXPERIMENT.md).
5. **Record your decision.** What did you observe? What did you change? What will you keep, change, or investigate next, and what evidence supports that choice?

When saving output, check your current folder: `runs/initial/` is relative to the
repository root; from inside `task2/` the same folder is `../runs/initial/`.
For example, in a macOS or Linux shell, run these **from the repository root**.
Choose new filenames if these already exist: redirection overwrites them.

```sh
mkdir -p runs/initial
(cd task2 && python3 incident.py) > runs/initial/incident.log 2>&1
printf '%s\n' "$?" > runs/initial/incident.exit
```

The log captures both output streams; the exit file records the incident command's
status, expected to be 1 in the starter. Run the focused test separately. On
Windows, ask your agent to capture both streams and the exit status for your shell.

To start task 2, point your agent at this repository and paste:

> In this cloned repository, help me investigate task 2 and improve how I work with you. First ask for my usual approach and expectation, or let me mark them unknown; record the starting commit or folder, start time, and a short note in `runs/RESULT.md`. Try to preserve a clean copy of the whole repository in a separate sibling folder without overwriting anything; if blocked, note it and continue. Create `runs/initial/` and `runs/changed/`. From `task2`, run `python3 incident.py` and the focused lost-ack test in TASK.md separately; save stdout, stderr, and each exit status in `runs/initial/`. Explain what happened briefly, then help me solve it normally. Keep supplied tests intact. Save this first attempt's checks and changes in `runs/initial/` too; reserve `runs/changed/` for my later workflow experiment. Help me preserve our interaction for a fresh-chat retro. My observation and final choice are mine.

For task 1, paste:

> In this cloned repository, help me investigate task 1 and improve how I work with you. First ask for my usual approach and expectation, or let me mark them unknown; record the starting commit or folder, start time, and a short note in `runs/RESULT.md`. Try to preserve a clean copy of the whole repository in a separate sibling folder without overwriting anything; if blocked, note it and continue. Create `runs/initial/` and `runs/changed/`. From `task1`, run `python3 -m unittest discover -s tests -v`; save stdout, stderr, and exit status in `runs/initial/`. Explain what happened briefly, then help me solve it normally. Keep supplied tests intact. Save this first attempt's checks and changes in `runs/initial/` too; reserve `runs/changed/` for my later workflow experiment. Help me preserve our interaction for a fresh-chat retro. My observation and final choice are mine.

If your agent cannot export a transcript, ask it to save a clearly labelled
summary, actual commands and outputs (including exit status), changes from the
recorded baseline, and copies of relevant new files in `runs/initial/`. Mark
missing details unknown. Tell the new chat exactly where to find these files, or
attach them. A new chat does not automatically see the old one; see [RETRO.md](RETRO.md).

## What counts as progress?

- **Incident checked:** task 2 starts with one delivery and zero retries. A repaired incident retries the same notification once and acknowledges it once. This local check does not prove durable reporting.
- **Implementation checked:** run the full supplied suite from your selected task and inspect its output. Green tests cover the listed examples, not every possible behavior; task 2's complete [contract](task2/CONTRACT.md) is available from the start.
- **Challenge a result:** after a green suite, or for a repaired slice, [choose a contract claim and try another case](task2/TASK.md#challenge-a-result). A useful check can pass, fail, or remain inconclusive.
- **Workflow learned:** record one observation grounded in your interaction, try one change, and state what happened or what remains unknown. You can do this even if the code is unfinished or your current workflow is already useful.

If you saw the task-1 demo, label a replay as prior exposure. Task 1 and task 2 are different problems, so their timings do not measure a workflow improvement. Keep supplied tests intact; add checks when useful.

Optional: from this repository root, `python3 check.py task2 --record runs/initial/tests.json` saves structured full-suite evidence. Choose a new path each time; this measures test execution only, not solving time. The plain unittest command also works.

## If you get stuck

- Check `python3 --version` (Windows: `py -3 --version`) is 3.11 or newer, and run the command in the selected task folder.
- An import error or zero discovered tests suggests the wrong folder or Python setup. Ask your agent to show the current folder and exact error, or ask the presenter.
- Keep your original files and outputs. A partial attempt, failed experiment, or decision to keep your current approach is useful evidence.

At the closing Q&A, sharing is optional: **I changed ___; I observed ___; I would use it again when ___; I still don't know ___.** You can continue later.

Prototype status: participant comprehension, difficulty, and classroom timing have not been human-tested.
