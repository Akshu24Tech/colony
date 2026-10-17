"""Build a short briefing any agent can read before it starts work."""
from __future__ import annotations

from pathlib import Path

from . import claims
from .antmill import find_loops
from .gitlog import read_changes

LABEL = {"verified": "OK", "corroborated": "corroborated, not verified", "unverified": "unverified",
         "disputed": "DISPUTED", "contradicted": "DO NOT TRUST", "quarantined": "QUARANTINED"}


def line(c: dict) -> str:
    extra = f" [{', '.join(c['paths'])}]" if c["paths"] else ""
    if c["status"] == "corroborated":
        extra += f" (agreed: {', '.join(c['agree'])})"
    if c["status"] == "disputed":
        extra += f" (disputed by: {', '.join(c['disagree'])})"
    return f"- [{LABEL[c['status']]}] {c['text']}{extra} (by {c['agent']})"


def build(repo: str = ".", recent: int = 8, limit: int = 300) -> str:
    changes = read_changes(repo, limit)
    seen: dict[str, tuple[str, str]] = {}
    for c in changes:
        seen[c.commit] = (c.agent, c.subject)
    recent_commits = set(list(seen)[-recent:])
    hot = sorted({c.path for c in changes if c.commit in recent_commits})

    lines = ["# Colony brief", ""]
    if claims.is_frozen(repo):
        lines += ["**FROZEN: shared writes are paused. Do not add claims, lessons or reviews. Tell the user.**", ""]
    lines += ["## Recent work (who did what)"]
    lines += [f"- {h[:8]} [{a}] {s}" for h, (a, s) in list(seen.items())[-recent:]]
    loops = find_loops(changes)
    lines += ["", "## Loop warnings"]
    lines += [f"- {f.kind}: {f.path} flipped {f.flips}x between {', '.join(f.agents)} - stop and decide who owns it"
              for f in loops] or ["- none detected"]

    lessons = claims.lessons_for(repo, hot)[:10] if hot else []
    lines += ["", "## Lessons for recently touched files"]
    lines += [line(c) for c in lessons] or ["- none"]

    everything = claims.current(repo)
    facts = [c for c in everything if c["kind"] != "lesson" and c["status"] != "quarantined"]
    lines += ["", "## Claims (best-supported first; never rely on DO NOT TRUST)"]
    lines += [line(c) for c in sorted(facts, key=lambda c: claims.ORDER[c["status"]])] or ["- none recorded"]
    held = [c for c in everything if c["status"] == "quarantined"]
    if held:
        lines += ["", f"## Quarantined ({len(held)}, dormant: kept for history, do not rely on them)"]
        lines += [line(c) for c in held[:5]]
    text = "\n".join(lines) + "\n"
    out = Path(repo) / ".colony" / "brief.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return text
