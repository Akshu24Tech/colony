"""Claims and lessons: notes agents want others to rely on, each with an optional check.

Append-only JSONL in .colony/claims.jsonl. Status is derived, never declared. Evidence beats agreement:

  contradicted  a check ran and failed -> do NOT rely on it (nothing can outvote this)
  verified      a check ran and passed
  disputed      an independent model family disagreed
  corroborated  >= 2 independent model families agreed (a weaker signal than verified)
  unverified    anything else
  quarantined   set aside by a human or by `colony reset`; kept for history, hidden from agents

Check formats: file:<path>  grep:<regex>::<path>  commit:<sha>  cmd:<shell command> (needs --allow-cmd)
A *lesson* is a claim with kind="lesson" and paths, e.g. "retry loop needed because API rate-limits" -> src/api.py.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from pathlib import Path

STORE = Path(".colony") / "claims.jsonl"
FREEZE = Path(".colony") / "FREEZE"


class Frozen(RuntimeError):
    """Raised when an agent tries to write while the colony is frozen."""
MIN_FAMILIES = 2  # independent model families needed to call a claim "corroborated"
ORDER = {"contradicted": 0, "disputed": 1, "verified": 2, "corroborated": 3, "unverified": 4, "quarantined": 5}

# Same-family models share training data and blind spots, so their agreement is not independent.
FAMILIES = (("claude", "anthropic"), ("anthropic", "anthropic"), ("gemini", "google"),
            ("antigravity", "google"), ("gpt", "openai"), ("codex", "openai"), ("openai", "openai"),
            ("llama", "meta"), ("qwen", "alibaba"), ("deepseek", "deepseek"),
            ("mistral", "mistral"), ("grok", "xai"))


def family_of(agent: str) -> str:
    a = agent.lower()
    return next((fam for key, fam in FAMILIES if key in a), "unknown")


def _path(repo: str) -> Path:
    return Path(repo) / STORE


def is_frozen(repo: str) -> bool:
    return (Path(repo) / FREEZE).exists()


def freeze(repo: str) -> None:
    p = Path(repo) / FREEZE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(int(time.time())))


def thaw(repo: str) -> None:
    (Path(repo) / FREEZE).unlink(missing_ok=True)


def _guard_write(repo: str) -> None:
    if is_frozen(repo):
        raise Frozen("colony is frozen: shared writes are paused. Ask the user to run `colony thaw`.")


def events(repo: str) -> list[dict]:
    return _read(repo)


def _read(repo: str) -> list[dict]:
    p = _path(repo)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []


def _append(repo: str, event: dict) -> None:
    p = _path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(event) + "\n")


def add(repo: str, text: str, check: str | None, agent: str,
        kind: str = "fact", paths: list[str] | None = None) -> str:
    _guard_write(repo)
    cid = uuid.uuid4().hex[:8]
    _append(repo, {"type": "claim", "id": cid, "ts": int(time.time()), "agent": agent, "text": text,
                   "check": check, "kind": kind, "paths": paths or []})
    return cid


def review(repo: str, claim_id: str, verdict: str, agent: str, family: str | None = None) -> None:
    _guard_write(repo)
    if verdict not in ("agree", "disagree"):
        raise ValueError("verdict must be 'agree' or 'disagree'")
    claim = next((e for e in _read(repo) if e["type"] == "claim" and e["id"] == claim_id), None)
    if claim is None:
        raise ValueError(f"no such claim: {claim_id}")
    if claim["agent"] == agent:
        raise ValueError("an agent cannot review its own claim")
    _append(repo, {"type": "review", "claim": claim_id, "ts": int(time.time()), "agent": agent,
                   "family": family or family_of(agent), "verdict": verdict})


def _require_claim(repo: str, claim_id: str) -> None:
    if not any(e["type"] == "claim" and e["id"] == claim_id for e in _read(repo)):
        raise ValueError(f"no such claim: {claim_id}")


def quarantine(repo: str, claim_id: str, reason: str = "", agent: str = "human") -> None:
    """Set a claim aside. Allowed while frozen (it is a human/guard action). Nothing is deleted."""
    _require_claim(repo, claim_id)
    _append(repo, {"type": "quarantine", "claim": claim_id, "ts": int(time.time()), "agent": agent, "reason": reason})


def release(repo: str, claim_id: str) -> None:
    _require_claim(repo, claim_id)
    _append(repo, {"type": "release", "claim": claim_id, "ts": int(time.time())})


def check_results(repo: str) -> dict[str, str]:
    return {e["claim"]: e["status"] for e in _read(repo) if e["type"] == "verify"}


def run_check(repo: str, check: str, allow_cmd: bool) -> str | None:
    """Return 'verified' / 'contradicted', or None if the check was skipped."""
    kind, _, arg = check.partition(":")
    root = Path(repo)
    if kind == "file":
        return "verified" if (root / arg).exists() else "contradicted"
    if kind == "grep":
        pattern, _, rel = arg.partition("::")
        target = root / rel
        if not target.is_file():
            return "contradicted"
        return "verified" if re.search(pattern, target.read_text(errors="replace")) else "contradicted"
    if kind == "commit":
        r = subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{arg}^{{commit}}"], capture_output=True)
        return "verified" if r.returncode == 0 else "contradicted"
    if kind == "cmd":
        if not allow_cmd:
            return None  # agents write claims; never run their commands unless the human opts in
        r = subprocess.run(arg, shell=True, cwd=repo, capture_output=True, timeout=60)
        return "verified" if r.returncode == 0 else "contradicted"
    return None


def verify_all(repo: str, allow_cmd: bool = False) -> dict[str, int]:
    counts = {"verified": 0, "contradicted": 0, "skipped": 0}
    for c in (e for e in _read(repo) if e["type"] == "claim" and e.get("check")):
        status = run_check(repo, c["check"], allow_cmd)
        if status is None:
            counts["skipped"] += 1
            continue
        _append(repo, {"type": "verify", "claim": c["id"], "ts": int(time.time()), "status": status})
        counts[status] += 1
    return counts


def current(repo: str) -> list[dict]:
    events = _read(repo)
    checked = {e["claim"]: e["status"] for e in events if e["type"] == "verify"}
    held: dict[str, bool] = {}
    for e in events:
        if e["type"] == "quarantine":
            held[e["claim"]] = True
        elif e["type"] == "release":
            held[e["claim"]] = False
    out = []
    for c in (e for e in events if e["type"] == "claim"):
        author_fam = family_of(c["agent"])
        agree, disagree = set(), set()
        for r in (e for e in events if e["type"] == "review" and e["claim"] == c["id"]):
            if r["family"] in ("unknown", author_fam):
                continue  # cannot establish independence -> no weight
            (agree if r["verdict"] == "agree" else disagree).add(r["family"])
        chk = checked.get(c["id"])
        if held.get(c["id"]):
            status = "quarantined"
        elif chk == "contradicted":
            status = "contradicted"
        elif chk == "verified":
            status = "verified"
        elif disagree:
            status = "disputed"
        elif len(agree) >= MIN_FAMILIES:
            status = "corroborated"
        else:
            status = "unverified"
        out.append({**c, "kind": c.get("kind", "fact"), "paths": c.get("paths", []),
                    "status": status, "agree": sorted(agree), "disagree": sorted(disagree)})
    return out


def _overlap(a: str, b: str) -> bool:
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def lessons_for(repo: str, paths: list[str] | None = None, query: str = "",
                include_contradicted: bool = False) -> list[dict]:
    words = query.lower().split()
    hits = []
    for c in current(repo):
        if c["kind"] != "lesson" or (c["status"] in ("contradicted", "quarantined") and not include_contradicted):
            continue
        if paths and not any(_overlap(p, lp) for p in paths for lp in c["paths"]):
            continue
        if words and not all(w in c["text"].lower() for w in words):
            continue
        hits.append(c)
    return sorted(hits, key=lambda c: ORDER[c["status"]])
