# Colony

**Collective intelligence for coding agents that share one repo: what one learns, all can use, without spreading wrong notes.**

You use several agents (an IDE agent, a terminal CLI, Antigravity, different models). Each starts blank, and
sometimes they quietly undo each other's work. Colony gives them a shared, evidence-checked memory:
lessons any agent can look up, trust that comes from checks rather than agreement, and guards for when a loop or a bad note spreads.

> **Status: v0.1.0.** Every command is built and tested on synthetic repos (CI runs Python 3.9-3.12; only 3.12 was tested locally).
> **Not yet validated with real agents or on real multi-agent repos.** See [docs/handoff-test.md](docs/handoff-test.md) and [docs/evaluation.md](docs/evaluation.md).

## See it
Open [`demo/colony-demo.html`](demo/colony-demo.html) in a browser. Same wrong note, same agents, two kinds of memory.
It is an illustrative simulation with fixed rules: it shows the mechanism, not how often this happens.

## Quickstart
```bash
pip install -e .                 # Python 3.9+, no dependencies
colony init                      # creates .colony/, installs the commit-attribution hook
export COLONY_AGENT=claude-code  # set per agent so commits get an "Agent:" trailer

colony brief                                              # what an agent reads at session start
colony lesson add "API rate-limits at 5 req/s; keep the backoff" --path src/api.py --check commit:<sha>
colony lesson find --path src/api.py                      # any agent, before editing that file
colony claim "port is set in config.yml" --check "grep:port::config.yml"
colony review <claim-id> --verdict agree                  # an independent model family weighs in
colony verify                                             # run the checks
colony antmill                                            # agents flipping the same file back and forth?
colony ledger                                             # per-agent track record from evidence
```
Guards, for you rather than the agents: `colony freeze` / `thaw`, `colony quarantine <id>` / `release <id>`,
`colony reset [--loops-only] --yes`. Nothing is ever deleted; quarantined claims stay in the log.

## How the collective stays honest
- **Lessons:** failure-and-fix insights tied to files, with evidence (a commit, a grep).
- **Evidence beats agreement:** three models agreeing cannot outvote a failed check.
- **Diverse corroboration:** for claims no test can check, agreement from *different model families* counts; same-family or unknown agreement counts for nothing.
- **Antmill guard and reset:** if agents start undoing each other's edits, it says so, and `reset --loops-only` sets aside the claims about those files.
- **Ledger:** counts from git and check results, never self-reported.

## Use it as a skill
Copy `skills/colony/` into your agent's skills folder (Claude Code: `~/.claude/skills/colony/`).
For agents without skills, paste [docs/AGENTS-snippet.md](docs/AGENTS-snippet.md) into their rules file.

## Why not just AGENTS.md or another memory tool?
Those exist, and so do many shared-memory tools ([related work](docs/related-work.md)). Colony's bet is narrow:
trust by evidence, not agreement, plus guards. Whether it beats a hand-written AGENTS.md is exactly what `eval/` is for.

## Inspiration
The film *Colony* (2026): shared knowledge across a hive, and the "ant mill" failure mode. See
[docs/film-notes.md](docs/film-notes.md). The film is the pitch, not the evidence.

## Tests
```bash
PYTHONPATH=src python -m unittest discover -s tests
python eval/run_eval.py --agent-cmd 'python3 {root}/eval/mock_agent.py {prompt}'   # harness plumbing
```

## License
MIT. Replace `<YOUR NAME>` in LICENSE before publishing.
