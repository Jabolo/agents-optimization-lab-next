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
- **Want to challenge a green result?** Use the short exercise below to choose
  a contract claim, inspect its coverage, and try an additional case. You can
  also do this for a repaired slice while the full suite is still red.
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

## Challenge a result

Pick a behavior you care about and ask: **what could still go wrong even though
this check passed?** You can use the same agent or a fresh chat. Give a fresh
chat the contract, solution changes (including new files), and actual test
results; it cannot see the previous interaction automatically.

One technique to try is a **boundary map**: compare what the contract requires
at different places data or state enters or changes with what the code and tests
actually do. This is a starting point, not a required tool or a promise to find
a defect. You might instead try a different agent, model, tool, skill, or technique.
Choose one change you want to evaluate and note what you expect it to help with.

If you choose the boundary map:

1. Ask your agent to make a map of three to five different paths
   where data or state enters or changes. Consider both new inputs and existing
   persisted state, if the contract applies. For each path, compare the relevant
   contract rule and failure behavior with the implementation and the actual
   supplied test bodies. For each, label a direct example found, an uncertainty,
   or a possible mismatch supported by specific evidence. A missing match in a
   quick search is a lead, not proof. Have it rank two or three specific cases by
   risk and evidence, then choose one yourself. Narrow the map if time is short.
2. Before running a new case, ask what inputs, expected outcome and preserved
   state follow from that requirement. Ask why existing checks might miss it.
   Review the expectation against the contract. Avoid requiring an internal table
   or implementation detail unless the contract requires it.
3. Ask the agent to create and run a small, reproducible check of your chosen
   claim using public interfaces and temporary data. Keep supplied tests and the
   solution unchanged during the check. Save the check, command, output and exit
   status under `runs/changed/` at the repository root if this is your workflow
   experiment, or with your first attempt's evidence if not. If the agent cannot
   write there, use a location you can write to or save a note; mark the case as
   proposed, not run, if you cannot execute it.
4. If it fails, decide whether the result shows a setup problem, a mistaken test
   expectation, or a possible contract violation. Investigate or fix it if worth
   the effort; keep the original output. If it passes, note exactly which case it
   covered; try another claim if it is worth the effort. Either way, decide what
   evidence you would need before accepting or stopping. One extra case cannot
   prove the whole service correct.

Optional starting prompt:

> Help me challenge my current task-2 result using a small boundary map. From
> the public contract, identify three to five different paths where data or
> state enters or changes, considering new inputs and existing persisted state
> where relevant. For each, cite the requirement and compare its validation or
> failure behavior with the implementation and relevant supplied test bodies.
> For each, label a direct example found, an uncertainty, or a possible mismatch
> supported by specific evidence. Rank two or three concrete cases by risk and
> evidence, explain the uncertainty, and let me choose one. Do not assume there
> is a defect, modify the solution or supplied tests, or use private materials.

After choosing, ask for the concrete case and expected behavior first, then ask
the agent to run it and preserve the evidence. Compare this workflow with your
usual approach: what did it help you see, what did it cost in time, effort, or
visible usage, and would you keep, change, or remove it? Unknown cost is fine.
You can turn a useful practice into your own prompt or skill for a later task.
If time is short, one inspected claim and a recorded next check are useful progress.
