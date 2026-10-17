# Fallback for agents that do not load skills

Paste this into `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `.cursorrules`:

```
Before starting work, run `colony brief` and read it. Do not rely on claims marked
"DO NOT TRUST". Before re-editing a file another agent changed, run `colony antmill`;
if it reports PINGPONG or CHURN for that file, stop and ask the user. When done, commit
(with COLONY_AGENT set) and record key facts with `colony claim ... --check ...`.
```
