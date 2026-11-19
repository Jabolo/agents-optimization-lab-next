# Question the interaction in a fresh chat

A new chat cannot automatically see your earlier chat. Before asking for advice,
package the real evidence so the fresh chat can verify what happened instead of
guessing.

## 1. Collect complete workspace changes (avoid `git diff` blind spots)

A plain `git diff` misses staged, committed, untracked, and ignored files
(including `runs/`). Run these from the repository root:

```sh
git status --short --ignored
git diff <baseline-commit>
```

*Using GitHub Download ZIP (no `.git/` folder)?* Skip the `git` commands, list
changed/new files against your untouched second ZIP copy (for example
`diff -ru <clean-copy> .`), and inspect `runs/initial/` directly.

## 2. Package the interaction and raw logs

Choose the path that matches your fresh chat (in the 30-minute room, **do not spend the 2-minute save cue running a full export**; keep your Room chat tab open or grab the fast summary below and run Step 3 in the vibe lounge):

- **Fast path (recommended when your fresh chat can access this workspace — ~15s):**
  Your fresh chat can read `runs/initial/` and run `git status --short --ignored` and `git diff <baseline-commit>` on demand. Keep the Room chat tab open or paste this short prompt:

  > Save a brief factual handoff in `runs/initial/summary.md` (or reply inline): scope worked, modified/new file paths, exact check commands with verbatim method counts and exit codes under `runs/initial/`, remaining gaps, and `unknown` for omissions. Do not export full diffs or edit `runs/RESULT.md`.

- **Full export path (only if your fresh chat cannot access your workspace):**
  Ask your implementation agent to save a clearly labeled interaction summary,
  commands, raw outputs with exit codes, `git status --short --ignored`, diff from
  baseline, and relevant untracked files in `runs/initial/`:

  > Package our interaction for a fresh-chat retro in `runs/initial/`: save a
  > clearly labeled summary, exact commands, raw outputs with exit statuses,
  > `git status --short --ignored`, `git diff <baseline-commit>` (or changed/new
  > files if there is no `.git/`), and paths to relevant new files. For a chat
  > without workspace access, also save or attach the contents of those files,
  > labeled with their original paths. Include only files I choose to share; mark
  > omissions `unknown`. Quote counts and exit codes verbatim from the raw logs.
  > Do not invent a transcript or my personal observations.

  *Fallback if your agent cannot write into `runs/initial/`:* ask it to print that
  labeled package directly in chat so you can paste or save it yourself, and mark
  missing files `unknown`.

## 3. Run the fresh-chat analysis

- **If the fresh chat can access your workspace:** tell it the exact paths to
  read—`runs/initial/`, `runs/RESULT.md`, the selected task card (`task1/TASK.md`
  or `task2/TASK.md` plus `task2/CONTRACT.md`), and the supplied `tests/*.py`
  files (`task1/tests/test_stock.py` or `task2/tests/*.py`) so it can verify test
  coverage directly.
- **If the fresh chat cannot access your workspace:** attach or paste those saved
  files, the contents of relevant new files, the task card/contract, and relevant
  `tests/*.py` files. Label paths and mark any omitted evidence unknown.

Paste and question the answer:

> Analyze how I used my coding agent on this task using the saved evidence in
> `runs/initial/`, `runs/RESULT.md`, the task card/contract, and the relevant
> `tests/*.py` files. Where did my instructions, context, model/tool choices, or
> checks create friction or unnecessary work? Quote numbers, counts, and exit
> codes verbatim from raw logs without smoothing or paraphrasing. Cite specific
> interaction excerpts, changes, or command results; separate observed facts
> from hypotheses and missing evidence. What worked well? Suggest one small
> workflow change worth testing next in `EXPERIMENT.md`, its expected benefit,
> likely overhead, and how I could tell whether it helped. Ask me about missing
> context.

Follow up critically:
- What evidence contradicts that advice?
- Could the agent already do this without adding another step?
- What should I **remove** instead of adding?
- What result would change my mind?

Pick **one** change yourself in [EXPERIMENT.md](EXPERIMENT.md) and record your
baseline note in [RESULT-TEMPLATE.md](RESULT-TEMPLATE.md) (`runs/RESULT.md`).
A critique is a hypothesis; testing it is the next step, and keeping your
current workflow is a valid conclusion.
