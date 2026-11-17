# Question the interaction in a fresh chat

Give a new chat the relevant conversation/transcript (or clearly labeled
summary), task contract, diff, commands and actual output. A new chat cannot
automatically see the previous one. If using the same workspace, identify exactly
which artifacts it should inspect. Save observations before accepting advice.
If a transcript is unavailable, label a concise summary as such. Include relevant
untracked files as well as the diff; a diff alone may not contain them.

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
