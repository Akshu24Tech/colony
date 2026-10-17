# Evaluation plan: does the colony beat its best single agent?

"Collective intelligence" is a claim, not a label. It only holds if the group outperforms its best member.
Until we measure this, Colony is shared notes with guards.

## Setup
Take 8-10 small tasks in a repo, each seeded with a known pitfall (a rate limit, a misleading comment,
a config that must not change). Run each task in three arms, with the same agents and models:
1. **Alone:** one agent, no shared state.
2. **AGENTS.md:** one agent with a hand-written notes file (the strong baseline people already use).
3. **Colony:** several agents handing off, using briefs, lessons and reviews.

## Measure
- Repeated mistakes: the same pitfall hit twice across agents.
- Wrong-note adoption: an agent acts on a false claim that was planted.
- Steps and tokens to finish.
- Review value: did independent-family reviews flag planted false claims that had no check?

## Decision rules (written before running)
- If Colony does not beat arm 2 on repeated mistakes, say so in the README and rethink.
- Report all runs, including ones where Colony lost. Small samples: show raw counts, not percentages.

## Harness (built)
`eval/run_eval.py` runs 4 seeded tasks (2 with a true lesson, 2 with a false note) across the three arms and
scores the final repo state with a shell check.
```bash
python eval/run_eval.py --agent-cmd 'python3 {root}/eval/mock_agent.py {prompt}'    # plumbing test
python eval/run_eval.py --agent-cmd '<your agent CLI, non-interactive mode> {prompt}' --repeats 5
```
**Status:** verified with a scripted mock agent only. A no-op agent fails every task, so the checks are not trivial.
The mock's pass/fail pattern is built in, so it shows the harness works, not that Colony works.
Known weaknesses: four tasks is tiny, the Colony arm gets an instruction the notes arm lacks (the shipped
AGENTS snippet), and real agents may find the answer on their own by reading code. Add harder tasks before drawing conclusions.
