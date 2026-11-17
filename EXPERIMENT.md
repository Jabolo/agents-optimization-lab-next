# One improvement experiment

Before starting, name your task and what you expect from your usual approach.
Record agent/model/settings where exposed; unknown is acceptable. Save the first
test result, first attempt's final checks, implementation changes, and interaction
or an honest summary in `runs/initial/`; keep the later experiment's evidence
separately in `runs/changed/`.

After the fresh-chat retro, choose **one** change: for example clearer acceptance
criteria, a different model, an earlier targeted check, a fresh reviewer, a small
reusable skill, or less planning. State the expected benefit and possible cost.

For example: “My agent reported success but showed no check output. I expect
asking for the actual result to make review clearer; it may add a tool call.”
Try that one request, retain the command and output, and decide whether it gave
you useful evidence. This is an illustration, not a claim that it saves time or
the change you must choose.

Choose a practical route:

- **Adapt:** apply the change to your current attempt or its next review/check,
  even if tests are already green, and observe what happens. This tests usefulness
  at that moment, not total-time superiority.
- **Repeat:** use an untouched copy of the whole repository in a separate sibling
  folder and a fresh implementation chat. Use the changed workflow. The whole
  repository keeps task links, guides, and agent instructions together. Never copy
  a repository inside itself or overwrite your first attempt or an existing folder.
  A fresh clone checked out at the recorded baseline commit works; for a downloaded ZIP,
  extract the same archive a second time into a new folder. Verify the starter
  files/commit match. If no clean baseline is available, record that limitation
  and use Adapt, or stop and ask for help.

For repeat, keep task, requirements, supplied tests, and environment constant.
Record any solution exposure or retained memory. If you also change the model,
prompt, and framework, label it a combined experiment; it cannot isolate effects.
Task 1 versus task 2 is not a controlled comparison.

Measure only what you can observe:

| Measure | Definition |
| --- | --- |
| Time | Wall-clock start to stop, including checking; mark pauses, setup, and retro separately |
| Human effort | Count substantive steering/correction messages; separately note active review minutes |
| Outcome | Exact command, exit status, raw test summary, and named contract gaps; keep unsuccessful attempts |
| Cost | Provider-reported task cost/tokens if available, including review; otherwise unknown |
| Change | Files changed, surprising behavior, extra complexity, and checks you added |

Unittest counts test methods and can report several failing subtests per method.
Do not subtract failure/error records from methods run to calculate passes.
Implementation exceptions can be intentional starter errors; import/setup errors
are different. Optional `check.py` records method outcomes separately from
failure/error records and fingerprints task files; its elapsed time is only suite
runtime. Record solving and retro intervals yourself. Added tests change the
oracle, so disclose them and retain supplied-suite results for comparisons.

Same tests and a smaller elapsed time are useful observations. One repeat is not
proof that the workflow caused a speedup: familiarity, cache, randomness, latency,
and human assistance also matter. Local measurements are personal evals, not a
cross-participant model leaderboard. For a stronger later study, use multiple
matched trials and vary order; distinguish held-out problems from familiar ones.

Stop with evidence and a next move even if tests remain red. Quality and effort
matter alongside speed. A change that adds overhead without value can be removed.
