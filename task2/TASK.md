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

**Start here:** open the repository root in your existing coding agent. From the
`task2` folder, run (or ask the agent to run):

```sh
python3 incident.py
```

The starter is intentionally broken. The command uses temporary local files and
exits with code 1. Expect a lost acknowledgement, one delivery before restart,
zero on retry, and `INCIDENT: the committed notification could not be safely
retried.` Its receiver is an in-memory fake; the result alone does not prove
durable reporting or deduplication.

On Windows, use a verified Python 3.11+ command such as `py -3` in place of
`python3`. No packages, server, or new account are required.

## What to do

1. Before editing, note your usual agent workflow, your expectation, and the start
   time. For a possible repeat, keep an untouched copy of the whole repository in
   a separate sibling folder; do not overwrite an existing folder. If you cannot
   make one, note that and continue with the Adapt route in EXPERIMENT.md.
2. Run the incident. Ask your agent what the output shows and what check could
   verify a repair. Decide how you want to work, then let your agent help normally.
3. To run one relevant failing test, from this folder use:

   ```sh
   python3 -m unittest discover -s tests -p test_recovery.py -k lost_ack -v
   ```

   The initial result is a failure: it expected a retry delivery but saw none.
   Work on this path, or choose another issue from the full contract. Run checks
   and inspect their actual output; add your own tests when useful.
4. Save the relevant interaction, diff, and output. Give them to a **new chat**
   using [RETRO.md](../RETRO.md). Pick one workflow change and use
   [EXPERIMENT.md](../EXPERIMENT.md) to try it. Record what happened, the effort
   and cost if visible, and what remains uncertain. Keep your notes locally.

Use every agent capability available to you. The agent may propose or carry out
the work you authorize; your expectation, evidence assessment, and choice of what
to keep or change belong to you.

## Check where you are

- **Incident repaired:** `python3 incident.py` exits 0 and says the original
  notification was preserved for retry. Run the focused test above too. These
  checks cover that example, not the whole service.
- **Full task green:** `python3 -m unittest discover -s tests -v` passes all
  supplied tests. The complete public requirements are in [CONTRACT.md](CONTRACT.md).
  Keep the supplied tests intact. Green tests are evidence for those cases, not
  proof that all failure paths are correct.
- **Another check:** after a repair, optionally run `python3 replay.py`. This
  disclosed scenario checks a different persisted migration, lost acknowledgement,
  restart, duplicate delivery, stock, and reporting outcome under the same public
  contract. A pass covers that scenario; it is not an independent hidden test.
- **If your agent finishes quickly:** choose one behavior from the contract that
  your checks may not cover. Ask your agent to construct another concrete case,
  run it, and explain what its result establishes. Check its assumptions against
  the contract: a probe tied to one internal table may not apply to another valid
  implementation. Decide whether the evidence changes your acceptance or next
  check. An agent can help, but the choice is yours.
- **Lab outcome:** you can name one workflow habit or experiment, an observation
  supported by a real output or interaction, and what you will keep, change, or
  investigate next. You can reach this outcome while some tests remain red.

New to this kind of service? Start with the incident and focused test; ask your
agent to explain their output and suggest a next check. Want a deeper challenge?
Inspect the migration, delivery, and online rebuild requirements in the contract,
choose an invariant, and try to falsify your agent's proposed repair. In both
cases, the point is to learn from **how** you worked.

The presenter will leave time for voluntary sharing and Q&A. You can keep working
at your own pace and continue after the session.
