---
name: colony
description: Shared, evidence-checked project state for work spread across several AI coding agents or models. Use at the START of any session in a git repo that other agents also edit (read the briefing), at the END of a session (record what you did and any claims others will rely on), and BEFORE re-editing a file that another agent recently changed (check for loops). Trigger whenever the user mentions switching between agents or models, handoffs, "what did the other agent do", agents undoing each other's work, or keeping several agents in sync, even if they never say "colony".
---

# Colony

Several agents (different tools, different models) work on one repo. Each starts blank.
Colony gives every one of them the same picture, built from evidence (git history, checks that
actually run), not from what an agent says about itself.

Requires the `colony` CLI (`pip install colony-agents`, or run from the repo with `PYTHONPATH=src`).

## At the start of a session

1. Run `colony brief` and read it before touching code. It lists recent work by agent,
   loop warnings, and claims with their status.
2. If the brief says **FROZEN**, shared writes are paused: do not add claims, lessons or reviews, and tell the user.
3. Trust claims by status:
   - `OK` — a check passed; fine to rely on.
   - `corroborated` — two independent model families agreed, no check ran. Useful, but weaker than `OK`.
   - `unverified` — a lead, not a fact. Confirm before building on it.
   - `DISPUTED` — an independent model disagreed. Look at it yourself.
   - `DO NOT TRUST` — a check failed. Do not rely on it; tell the user it is wrong.
   - `QUARANTINED` — set aside by the user or by a reset. Ignore it.
4. Before editing a file, run `colony lesson find --path <file>`. Another agent may already have learned
   the hard way why it is written like that. Follow `OK` lessons; treat the rest as leads.
5. If a loop warning names a file you were about to edit, stop and tell the user which agents are
   flipping it. Do not make another edit to that file until they decide who owns it.

## While working

Before re-editing a file another agent changed recently, run `colony antmill`. If it reports
`PINGPONG` or `CHURN` for that file, do not "fix it back". Explain the disagreement to the user instead.

## At the end of a session

1. Commit your work. Commits are attributed by the `Agent:` trailer, which the hook adds when
   `COLONY_AGENT` is set in your shell. If it is not set, say so to the user rather than guessing a name.
2. If you fixed something that cost you effort, share it so no other agent repeats it:

   ```
   colony lesson add "API rate-limits at 5 req/s; keep the backoff" --path src/api.py --check commit:<sha-of-your-fix>
   ```

3. If a claim in the brief affects your work and you have formed your own view, record it:
   `colony review <claim-id> --verdict agree|disagree`. Review only after your own assessment, never to be polite.
   You cannot review your own claims, and agreement from your own model family adds no weight.
4. Record only what future agents need and cannot easily see in the code, each with a check when one exists:

   ```
   colony claim "API base URL is set in config.yml" --check "grep:base_url::config.yml"
   colony claim "build passes" --check "cmd:make test"      # cmd checks only run if the user runs `colony verify --allow-cmd`
   ```

5. Run `colony verify` and mention any `contradicted` claim in your summary.

## Rules

- Agreement never outvotes a failed check. Evidence wins.
- Never mark a claim verified yourself. Status comes only from `colony verify`.
- Never put secrets in claims. The file is plain text.
- A claim without a check is allowed but stays `unverified`. Prefer a check.
- `colony reset`, `quarantine` and `freeze` are the user's tools. Suggest them when a loop or a bad claim keeps spreading; do not run them yourself.
- Do not delete `.colony/claims.jsonl` entries. It is append-only so mistakes stay visible.
