"""Per-agent track record, computed from evidence (git history and check results), never self-reported.

These are counts, not rankings. Small samples mislead; read them next to the history.
"""
from __future__ import annotations

from collections import defaultdict

from . import claims
from .gitlog import read_changes


def build(repo: str = ".", limit: int = 500) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(lambda: {
        "commits": set(), "files_changed": 0, "undone_by_other": 0, "undid_other": 0,
        "claims_verified": 0, "claims_failed": 0, "lessons": 0, "reviews_right": 0, "reviews_wrong": 0})
    by_path = defaultdict(list)
    for c in read_changes(repo, limit):
        stats[c.agent]["commits"].add(c.commit)
        stats[c.agent]["files_changed"] += 1
        by_path[c.path].append(c)
    for seq in by_path.values():
        for a, b in zip(seq, seq[1:]):
            if a.old != a.new and b.new == a.old and a.agent != b.agent:
                stats[a.agent]["undone_by_other"] += 1
                stats[b.agent]["undid_other"] += 1

    checks = claims.check_results(repo)
    log = claims.events(repo)
    for e in log:
        if e["type"] == "claim":
            if e.get("kind") == "lesson":
                stats[e["agent"]]["lessons"] += 1
            if checks.get(e["id"]) == "verified":
                stats[e["agent"]]["claims_verified"] += 1
            elif checks.get(e["id"]) == "contradicted":
                stats[e["agent"]]["claims_failed"] += 1
        elif e["type"] == "review" and checks.get(e["claim"]) in ("verified", "contradicted"):
            right = (e["verdict"] == "agree") == (checks[e["claim"]] == "verified")
            stats[e["agent"]]["reviews_right" if right else "reviews_wrong"] += 1
    return {a: {**v, "commits": len(v["commits"])} for a, v in sorted(stats.items())}


def render(table: dict[str, dict]) -> str:
    cols = [("commits", "commits"), ("files_changed", "files"), ("undone_by_other", "undone"),
            ("undid_other", "undid"), ("claims_verified", "ok"), ("claims_failed", "failed"),
            ("lessons", "lessons"), ("reviews_right", "rev+"), ("reviews_wrong", "rev-")]
    w = max([5] + [len(a) for a in table])
    out = ["agent".ljust(w) + "  " + "  ".join(h.rjust(7) for _, h in cols)]
    for a, v in table.items():
        out.append(a.ljust(w) + "  " + "  ".join(str(v[k]).rjust(7) for k, _ in cols))
    out.append("")
    out.append("undone/undid: changes reverted by / reverting a different agent. ok/failed: claims whose check passed/failed.")
    out.append("rev+/rev-: reviews that matched / contradicted a later check. Counts, not rankings.")
    return "\n".join(out)
