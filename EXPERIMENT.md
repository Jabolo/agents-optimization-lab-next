# One improvement experiment

After your fresh-chat [RETRO.md](RETRO.md) critique, pick **one** workflow
change to test and save its outputs separately in `runs/changed/` (leaving
`runs/initial/` untouched). State what you changed, what benefit you expect, and
its likely overhead before running it.

## Four equal experiment options

Choose the option that best targets the friction you observed—none is required or
assumed better in advance:

1. **Switch model or reasoning effort:** Try a faster/lighter or stronger/deeper
   model or reasoning setting on a comparable slice or review.
2. **Simplify or remove a noisy step:** Drop a prompt rule, tool, extra check, or
   full-suite run that added clutter or delay without changing your decision.
3. **Slice-first with `check.py -p/-k`:** Work on one failing slice at a time
   using targeted filters (for example `python3 check.py task2 -p test_recovery.py -k lost_ack`)
   instead of running the whole red suite repeatedly.
4. **Targeted verification or reusable instruction/skill:** Ask for raw
   contract-edge verification (for example [task2/TASK.md#challenge-a-result](task2/TASK.md#challenge-a-result))
   or capture one recurring friction into a short reusable local instruction or
   optional skill.

A change that adds overhead without useful evidence can be discarded.

## Choose a route: Adapt vs Repeat

- **Adapt (a practical starting point for a short session or sandboxed workspace):**
  Apply your one change to the current attempt or its next review/check (even if
  supplied tests are already green) and observe what it surfaces. This evaluates
  usefulness at that moment; do **not** compare Adapt's total elapsed time
  against your Initial attempt.
- **Repeat (allow more time, for example in the vibe lounge or later):** Start a fresh
  implementation chat in an untouched sibling copy of the whole repository
  (a fresh clone at your recorded baseline commit, or a second extraction of the
  same Download ZIP). Keep the task, requirements, and supplied tests constant
  where practical, and never copy a repo inside itself or overwrite your first
  attempt. Record unavoidable differences, prior exposure, or combined changes
  (varying model, prompt, and workflow together cannot isolate one cause).

## Measure and read outputs accurately

| Measure | Definition |
| --- | --- |
| Time | Wall-clock active work, pauses, and retro noted separately |
| Human effort | Substantive steering messages and active review minutes |
| Outcome | Exact command, exit status, raw test summary, and remaining contract gaps |
| Cost | Provider-reported tokens/cost if visible (including review); else `unknown` |
| Change | Files changed, extra complexity, and checks you added |

`check.py` (run from the repo root) supports `-p <pattern>` (filename filter)
and `-k <filter>` (test name filter), prints a 1-line `Summary` even without
`--record`, and writes structured JSON when given `--record <path>`. It splits
**`supplied` vs `added`** test methods, tracks `supplied_tests_intact` via file
fingerprints, and separates method outcomes from `unittest` failure/error
records.

Note why raw `unittest` output can mislead: `unittest`'s `Ran N tests` line
counts test **methods**, while a single method can emit multiple failing
`SUBTEST` records—never subtract failure/error counts from `Ran N` to estimate
passes. Also remember `check.py`'s `elapsed_s` is suite runtime only, not human
solving time.

Local measurements are personal evaluations, not a cross-participant model
leaderboard. Stopping with grounded evidence and a next move is success even if
tests remain red.
