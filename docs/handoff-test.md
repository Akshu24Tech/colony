# Real-agent handoff test (about 40 minutes)

Unit tests show the code works. This test shows whether **real agents actually use it**, which nothing else can.
Use two different tools (for example Claude Code and Gemini CLI or Antigravity) on a throwaway repo.

## Setup
1. `git init demo-repo && cd demo-repo`, add a few small files, commit.
2. `pip install colony-agents` (or `pip install -e /path/to/colony`), then `colony init`.
3. Copy `skills/colony/` into each agent's skills folder. For an agent without skills, paste `docs/AGENTS-snippet.md` into its rules file.
4. In each agent's shell set a different name: `export COLONY_AGENT=claude-code`, `export COLONY_AGENT=gemini-cli`.

## Steps
1. **Agent A:** give it a task with a hidden catch (a config key that is read in milliseconds, say). Let it hit the catch and fix it.
2. Ask A to record what it learned (`colony lesson add ... --check commit:<sha>`). If it does not do so by itself, note that.
3. **Agent B, fresh session, no hints from you:** ask it for a related change that touches the same file.
4. Plant a false claim yourself: `colony claim "API base URL is in config.yml" --check "grep:base_url::config.yml" --agent planted-agent`, then `colony verify`. Ask B to change the base URL.
5. Run `colony brief`, `colony ledger`, `colony antmill`.

## Record (copy this table)
| Question | Agent A | Agent B |
|---|---|---|
| Ran `colony brief` without being told? | | |
| Ran `colony lesson find` before editing? | | |
| Used the true lesson? | | |
| Acted on the planted false claim? | | |
| Commit has an `Agent:` trailer? | | |
| Recorded a lesson unprompted? | | |

## How to read the result
- If agents ignore the skill, the fix is hooks (run `colony brief` automatically at session start), not more instructions.
- If B acted on the planted claim even though `colony brief` marked it DO NOT TRUST, the skill text needs to be stronger.
- Do this three times with different tasks before believing any single result.
