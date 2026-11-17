# The Agents Optimization Lab

**Make the tests green. Then investigate how you worked and try one improvement.**

Use the coding agent you already know, with its normal capabilities. You need
Python 3.11+ and your existing authenticated agent. No packages or server needed.
Windows: replace `python3` with a verified Python 3.11+ command such as `py -3`.

1. Start with **task 1** for a small experiment, or **task 2** for a deeper challenge.
2. **Before editing**, note your usual approach, one expectation, and the start
   time. Keep an untouched copy of the selected task for a possible repeat.
   Copy [RESULT-TEMPLATE.md](RESULT-TEMPLATE.md) to `runs/RESULT.md`, or make a
   short note in your own format. Agent/model/settings may be unknown.
3. From that task's folder, run `python3 -m unittest discover -s tests -v` and
   save the initial output. Failing assertions and implementation exceptions are
   intentional. Missing Python, syntax/import errors, or undiscovered tests are
   setup problems. Then work normally and save your interaction and final output.
4. Use [RETRO.md](RETRO.md) in a fresh chat. Choose **one** improvement to try.
5. Follow [EXPERIMENT.md](EXPERIMENT.md), try the change, and record what happened.

You can give your agent this prompt (choose a task):

> Help me run task 1. Before editing, ask for my usual approach and expectation,
> or let me mark them unknown. Preserve a clean starter and initial test output.
> Then solve normally, keep supplied tests intact, and show actual check output.
> Help me save the interaction for a fresh-chat retro; do not invent my opinion.

Optional: from the repo root, `python3 check.py task1 --record
runs/initial/tests.json` saves structured check evidence. Use a different path
for the final/changed check; records are never overwritten. This measures **test
execution**, not time spent solving. The plain unittest command is sufficient.

Your goal is one useful observation about your workflow. Finishing both tasks
is optional. An incomplete attempt can still reveal something worth changing.
Green tests establish the listed behaviors, not complete correctness or a better
workflow. Inspect changes and add checks for gaps you find.

### Tasks

| Task | Start command from repo root | Challenge |
| --- | --- | --- |
| [1: stock movements](task1/TASK.md) | `cd task1` | Small function; retries and validation |
| [2: inventory reservations](task2/TASK.md) | `cd task2` | Durable state, conflicts, expiry, contention, events |

If the presenter demonstrated task 1, label your replay as practice with prior
exposure. Task 2 starts independently. Keep supplied tests intact; add tests when
needed. Fix implementation behavior rather than weakening assertions.

At the closing Q&A, optionally share: **I changed ___; I observed ___; I would
use it again when ___; I still don't know ___.** Continue later at your own pace.

Prototype status: task difficulty and classroom timing are not yet human-tested.
