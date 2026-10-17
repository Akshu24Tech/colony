"""Read git history into per-file change records (standard library only)."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

RS, US = "\x1e", "\x1f"
TRAILER = re.compile(r"^Agent:\s*(.+?)\s*$", re.I | re.M)
COAUTH = re.compile(r"^Co-authored-by:\s*(.+?)\s*<", re.I | re.M)
RAW = re.compile(r"^:\d+ \d+ ([0-9a-f]+) ([0-9a-f]+) [A-Z]\t(.+)$", re.M)


@dataclass(frozen=True)
class Change:
    commit: str
    agent: str
    date: str
    subject: str
    path: str
    old: str  # blob id before the commit (all zeros = file did not exist)
    new: str  # blob id after the commit


def git(repo: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)
    return r.stdout


def agent_of(author: str, body: str) -> str:
    """Who made this commit? An 'Agent:' trailer wins, then Co-authored-by, then the git author."""
    m = TRAILER.search(body) or COAUTH.search(body)
    return m.group(1) if m else author


def read_changes(repo: str = ".", limit: int = 500) -> list[Change]:
    fmt = f"--format={RS}%H{US}%an{US}%cI{US}%s{US}%B{US}"
    out = git(repo, "log", "--reverse", "--no-merges", "--raw", "--no-abbrev",
              "--no-renames", f"-n{limit}", fmt)
    changes: list[Change] = []
    for chunk in out.split(RS)[1:]:
        h, author, date, subject, body, raw = chunk.split(US)
        who = agent_of(author, body)
        for old, new, path in RAW.findall(raw):
            changes.append(Change(h, who, date, subject, path, old, new))
    return changes
