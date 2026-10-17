"""Detect 'ant mills': agents undoing and redoing each other's work on the same file.

A *flip* is a change that restores the exact content a file had before the
previous change. Two or more consecutive flips on one file mean the content is
oscillating (A -> B -> A -> B ...). If different agents alternate, that is a
ping-pong; if one agent does it alone, it is churn.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict

from .gitlog import Change


@dataclass
class Finding:
    path: str
    kind: str  # "pingpong" | "churn"
    flips: int
    agents: list[str]
    commits: list[str]


def find_loops(changes: list[Change], min_flips: int = 2) -> list[Finding]:
    by_path: dict[str, list[Change]] = defaultdict(list)
    for c in changes:
        by_path[c.path].append(c)

    findings: list[Finding] = []
    for path, seq in by_path.items():
        run, start = 0, 0

        def close(end: int) -> None:
            if run >= min_flips:
                span = seq[start:end + 1]
                agents = sorted({c.agent for c in span})
                kind = "pingpong" if len(agents) > 1 else "churn"
                findings.append(Finding(path, kind, run, agents, [c.commit[:8] for c in span]))

        for i in range(len(seq) - 1):
            a, b = seq[i], seq[i + 1]
            if a.old != a.new and b.new == a.old:
                if run == 0:
                    start = i
                run += 1
            else:
                close(i)
                run = 0
        close(len(seq) - 1)
    findings.sort(key=lambda f: (-f.flips, f.path))
    return findings


def to_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
