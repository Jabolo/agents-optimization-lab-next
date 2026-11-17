# One improvement experiment

Before starting, name your task and what you expect from your usual approach.
Record agent/model/settings where exposed; unknown is acceptable. Save the first
test result, implementation diff, and interaction or an honest summary in
`runs/initial/`; keep changed-attempt evidence separately in `runs/changed/`.

After the fresh-chat retro, choose **one** change: for example clearer acceptance
criteria, a different model, an earlier targeted check, a fresh reviewer, a small
reusable skill, or less planning. State the expected benefit and possible cost.

Choose a practical route:

- **Adapt:** apply the change to the current incomplete attempt and observe the
  next step. This tests usefulness at that moment, not total-time superiority.
- **Repeat:** start from the same untouched code/tests in a new folder and fresh
  implementation chat; use the changed workflow. Do not reset or overwrite your
  first attempt. A fresh clone at the same commit is useful after publication.

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
