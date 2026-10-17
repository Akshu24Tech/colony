"""Circuit breakers: reset a region the loop detector flagged, or the whole shared state.

The film's ant mill ends in a reset to a primitive state, not in deletion. Same here:
reset only *quarantines* (hides claims from agents, keeps them in the log). Nothing is erased.
"""
from __future__ import annotations

from . import claims
from .antmill import find_loops
from .claims import _overlap
from .gitlog import read_changes


def reset_plan(repo: str, loops_only: bool = False, limit: int = 500) -> list[dict]:
    """Claims that would be quarantined. Verified claims always survive: they are the baseline."""
    candidates = [c for c in claims.current(repo) if c["status"] in ("unverified", "corroborated", "disputed")]
    if not loops_only:
        return candidates
    flagged = [f.path for f in find_loops(read_changes(repo, limit))]
    return [c for c in candidates if any(_overlap(p, fp) for p in c["paths"] for fp in flagged)]


def apply_reset(repo: str, plan: list[dict], reason: str) -> int:
    for c in plan:
        claims.quarantine(repo, c["id"], reason, agent="colony-reset")
    return len(plan)
