# Task 2 — investigate a recovery incident

**Your goal:** use your coding agent on a difficult task, examine how you worked,
and try one change to your workflow. The task and its tests give you evidence for
that experiment. A complete repair is a useful target; a well-examined partial
attempt is also meaningful.

## The incident

A reservation was saved and its notification was delivered, but the sender lost
the acknowledgement. On retry, the notification is missing. The service also has
older data and a separate reporting database, so a repair needs more than a happy
path check.

**Run your first red checks right away:** from the repository root (on Windows,
use `py -3` instead of `python3`), run these separately because `incident.py`
is expected to exit with code `1`:

```sh
python3 task2/incident.py
python3 check.py task2 -p test_recovery.py -k lost_ack --record runs/initial/lost-ack.json
```

(Or from inside `task2/`, run `python3 incident.py` and `python3 -m unittest discover -s tests -p test_recovery.py -k lost_ack -v`, saving manual output to `../runs/initial/`.)

The starter is intentionally broken: `incident.py` uses temporary local files,
delivers once before restart and zero times on retry, and prints
`INCIDENT: the committed notification could not be safely retried.` Its receiver
is an in-memory fake, so a pass there alone does not prove durable reporting or
deduplication. The focused `lost_ack` check fails for the same missing retry.

> **Warning:** Running the full suite (`python3 check.py task2` or
> `python3 -m unittest discover -s tests -v`) upfront dumps ~1,800 lines of
> expected starter failures. Start with `incident.py` and the `lost_ack` check.

## What to do

1. **Observe the starter state first** with the two commands above (see
   [README.md](../README.md) for shell capture flags on macOS/Linux and Windows
   PowerShell).
2. **Jot a short baseline note** in `runs/RESULT.md` using
   [RESULT-TEMPLATE.md](../RESULT-TEMPLATE.md): task/commit, usual approach, and
   one expectation (`unknown` is fine). Note your start time if measuring time.
   If you plan a clean `Repeat`, keep an untouched sibling copy of the whole repo
   (or a second extraction of the same ZIP) before editing;
   if sandbox-blocked, note it and use `Adapt`.
3. **Work normally with your agent** on one bounded slice (a useful start in a
   short session) or the full [CONTRACT.md](CONTRACT.md). Run focused `-p`/`-k`
   checks as you go, keep supplied tests intact, and save this attempt's checks
   in `runs/initial/`.
4. **Retro and one experiment:** Ready to reflect, stuck, or finished? Run
   [RETRO.md](../RETRO.md) in a **fresh chat**, choose one workflow
   change in [EXPERIMENT.md](../EXPERIMENT.md) (`Adapt` or `Repeat`), save new
   evidence in `runs/changed/`, and record your decision in `runs/RESULT.md`.
   Continue in the vibe lounge if the room session ends first; keep your copy and
   notes so you can resume without starting over.

Use every agent capability available to you. Your expectation, evidence review,
and choice of what to keep or change belong to you.

## Check where you are

- **Incident repaired:** `python3 task2/incident.py` exits `0` and reports the
  original notification was preserved for retry, and the `lost_ack` check passes.
- **Full task green:** `python3 check.py task2` (from repo root) or
  `python3 -m unittest discover -s tests -v` (from `task2/`) passes all supplied
  tests against [CONTRACT.md](CONTRACT.md). Keep supplied tests intact.
- **Another check:** `python3 task2/replay.py` checks an additional disclosed
  migration, lost-ACK, restart, duplicate-delivery, stock, and reporting scenario
  under the same contract (not a hidden test).
- **Optional post-green check:** see [Challenge a result](#challenge-a-result)
  below, or choose another experiment in [EXPERIMENT.md](../EXPERIMENT.md).
- **Lab outcome:** you leave with one workflow change or observation backed by
  real output, even if some tests remain red.

## Challenge a result

Once a slice or the full suite is green, one optional post-green check (alongside
the other experiment options in [EXPERIMENT.md](../EXPERIMENT.md)) is a small
**boundary check** on a behavior you care about: *what could still go wrong even
though tests passed?*

1. **Inspect actual test bodies first:** Pick 2–3 contract rules (new inputs or
   persisted state) in [CONTRACT.md](CONTRACT.md) and compare them against your
   implementation and the actual supplied `tests/*.py` bodies—a quick search is
   only a lead, not proof.
2. **Define one concrete case before running it:** State the inputs, expected
   outcome, and preserved state from the contract. Avoid asserting uncontracted
   internal table names or schema details.
3. **Run a standalone check cleanly:** Create and run a small reproducible
   script using public interfaces and temporary DBs, keeping your solution and
   supplied tests unchanged. Save the check, command, output, and exit status in
   `runs/changed/` (or mark it proposed if execution is blocked).
4. **Classify the outcome:** Decide whether any failure is a setup error, wrong
   expectation, or real contract gap, and whether the check justified its effort
   compared to your usual workflow.

Optional prompt (use in the same chat or a fresh chat given the contract, diff,
and test output):

> Review 2–3 state or input paths in `task2/CONTRACT.md` against the code and
> actual `tests/*.py` bodies, and rank 2 concrete gaps or uncertainties without
> modifying the solution or supplied tests. Let me pick one case, define the
> contract expectation first, then run a standalone check saved under
> `runs/changed/`.
