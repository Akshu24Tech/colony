# Design notes

Colony is about **collective intelligence for coding agents**: what one agent learns, every agent can use,
without letting a wrong note spread. Sharing is the point; the guards are what make it safe.

## Principle: evidence over agreement
Other shared-memory tools raise trust when several agents agree. Agreement can be wrong
together (same model, same mistake) or circular (A confirms B confirms A). Colony only
raises trust when something outside the agents confirms a claim: a file exists, a pattern is
in the code, a command exits 0. Claims with no check stay `unverified`, and we say so.

## What each command does (v0.1.0)
| Command | What it does |
|---|---|
| `init` | creates `.colony/`, installs a `prepare-commit-msg` hook that adds `Agent:` trailers |
| `lesson add/find` | share a failure-and-fix insight tied to files; evidence such as `commit:<sha>` |
| `claim`, `verify` | record notes with checks (`file:`, `grep:`, `commit:`, `cmd:`); `cmd:` needs `--allow-cmd` |
| `review` | independent verdicts; only different model families count; cannot outvote a failed check |
| `brief` | recent work by agent, loop warnings, lessons for touched files, claims by status |
| `antmill` | flags files whose content flips back and forth (>= 2 consecutive flips) |
| `quarantine`, `release` | set one claim aside and bring it back; nothing is deleted |
| `reset [--loops-only]` | quarantine everything not verified, or only what touches looping files; `--yes` to apply |
| `freeze`, `thaw` | kill switch: agents cannot add claims, lessons or reviews while frozen |
| `ledger` | per-agent counts from evidence: reverts by others, claims that passed or failed, review accuracy |

All of it is tested on synthetic repos. None of it has been validated with real agents yet (`handoff-test.md`).

## Collective intelligence, defined narrowly
A group beats its best member only when members are diverse, independent, and their outputs are aggregated sensibly.
Colony applies that literally: reviews from the same model family or an unknown family carry no weight, two
independent families are needed for `corroborated`, and nothing but a passing check reaches `verified`.
Whether the colony actually beats its best single agent is an open question: see `evaluation.md`.

## Known limits (be honest in the README too)
- **Attribution is only as good as the trailer.** Without `COLONY_AGENT` set, commits fall back to the git author.
- **Antmill sees committed history only.** Uncommitted ping-pong in a working tree is invisible.
- **Flip = exact content restore.** Near-identical oscillation (whitespace, renamed variable) is missed.
- **Some real reverts are healthy.** Treat findings as "look here", not "something is broken".
- **Model family is inferred from the agent name** (a built-in list in `claims.py`); unknown names get no weight. Override with `--family`.
- **Corroboration is not truth.** Independent families can still share a wrong belief; that is why it ranks below `verified`.
- **Claims are plain text** in `.colony/claims.jsonl`. No secrets.
- **Skills are advisory.** An agent can ignore SKILL.md. Whether real agents follow it is the open test in `handoff-test.md`.
- **The ledger is descriptive.** Counts, not rankings; small samples mislead, and a revert is not always a mistake.

## Security
Agents write claims, so `cmd:` checks are untrusted input. They run only when a human passes `--allow-cmd`.

## Film notes
See `film-notes.md`. The film is the pitch; every feature has to stand on technical merit.
