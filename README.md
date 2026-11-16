# The Agents Optimization Lab

**Make the tests green. Then investigate how you worked and try one improvement.**

Use the coding agent you already know, with its normal capabilities. You need
Python 3.11+ and your existing authenticated agent. No packages or server needed.
Windows: replace `python3` with a verified Python 3.11+ command such as `py -3`.

1. Start with **task 1** for a small experiment, or **task 2** for a deeper challenge.
2. From that task's folder, run `python3 -m unittest discover -s tests -v`.
   Failing assertions are intentional. Import/setup errors are not the exercise.
3. Work as you normally would. Save the test output and relevant interaction.
4. Use [RETRO.md](RETRO.md) in a fresh chat. Choose **one** improvement to try.
5. Follow [EXPERIMENT.md](EXPERIMENT.md), and copy
   [RESULT-TEMPLATE.md](RESULT-TEMPLATE.md) to `runs/RESULT.md` for your short record.

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
