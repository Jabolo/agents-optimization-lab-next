# Question the interaction in a fresh chat

Give a new chat the relevant conversation/transcript (or clearly labeled
summary), task contract, diff, commands and actual output. A new chat cannot
automatically see the previous one. If using the same workspace, identify exactly
which artifacts it should inspect. Save observations before accepting advice.
If a transcript is unavailable, label a concise summary as such. Include relevant
new files as well as changes from the recorded baseline. A plain `git diff` may
miss staged, committed, untracked, or ignored files, including `runs/`. For
example, ask your agent:

> Save a clearly labelled interaction summary, the commands and actual outputs
> with exit statuses, changes from my recorded baseline, and relevant new files
> in `runs/initial/`. Mark missing evidence unknown. Tell me which files to give
> the fresh chat; do not invent a transcript or my personal observations.

Give that fresh chat the saved files and the selected task card, or identify
their exact paths if it can access your workspace. For task 2, also give it the
relevant contract. Keep the first attempt's final checks in `runs/initial/`;
`runs/changed/` is for the later experiment.

Try this and question the answer:

> Analyze how I used my coding agent on this task. Where did my instructions,
> context, tool/model choices, or checking create friction or unnecessary work?
> Cite specific interaction excerpts, changes, or command results. Separate
> observed facts from hypotheses and missing evidence. What did I do well?
> Suggest one small workflow change worth testing next, its expected benefit,
> likely overhead, and how I could tell whether it helped. Do not claim a speedup
> or cost saving from data I haven't supplied. Ask me about missing context.

Follow up: What evidence contradicts that advice? Could the agent already do this
without another step? What should I remove? What result would change my mind?

Choose one change yourself. A critique is a hypothesis; testing it is the next
step. It is fine to retain your approach or conclude the evidence is insufficient.
