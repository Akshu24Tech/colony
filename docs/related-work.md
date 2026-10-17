# Related work (checked October 2026)

Colony does not claim to be first. These projects solve neighbouring problems; please look at them.

| Project | What it does | How Colony differs |
|---|---|---|
| HiveMind (projectmentor/hive-mind) | P2P append-only shared memory; trust rises with independent corroboration. AGPL-3.0 | Colony raises trust from checks, not agreement. No code is shared. |
| Hivemind (Activeloop) | Captures agent traces, codifies skills, propagates across agents | They learn skills; Colony tracks project state and loops |
| Hive (rllm-org/hive) | Agents evolve a shared artifact judged by an eval script. Apache-2.0 | Colony is for ordinary projects with no eval harness |
| claude-flow / ruflo hive-mind | Queen-led orchestration with shared memory | Colony does not run your agents; it reads git |
| stalebrain, MemFalsify | Audit agent memory files against the repo | Colony checks claims at write time, across agents |
| loopsnare, Loop Engineering, CodeDecay | Loop and ping-pong detection inside agent traces or one orchestrated loop | Colony reads git, so it works across separate tools |
| routesmith, RightModel, codeprobe | Per-model outcome tracking and routing | Planned `ledger` will use Colony's own attribution |
| Roast Room (nateherkai), Room | Multi-agent debate skills | Not memory |

Re-check this list before each release; the space moves fast.
