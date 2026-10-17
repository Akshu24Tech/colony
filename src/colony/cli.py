"""colony: evidence-checked shared state and loop detection for coding agents."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from . import brief, claims, guard, ledger
from .antmill import find_loops, to_dicts
from .gitlog import git, read_changes


def _writes(fn):
    """Turn a frozen colony into a clear message and exit code 3 instead of a traceback."""
    def run(a) -> int:
        try:
            return fn(a)
        except claims.Frozen as e:
            print(f"error: {e}", file=sys.stderr)
            return 3
    return run


def cmd_init(a) -> int:
    Path(a.repo, ".colony").mkdir(exist_ok=True)
    hooks = Path(git(a.repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
    hooks.mkdir(parents=True, exist_ok=True)
    dest = hooks / "prepare-commit-msg"
    if dest.exists():
        print(f"hook already exists, left untouched: {dest}")
    else:
        shutil.copy(Path(__file__).with_name("prepare-commit-msg"), dest)
        dest.chmod(0o755)
        print(f"installed commit hook: {dest}\nSet COLONY_AGENT=<name> in each agent's shell so commits are attributed.")
    return 0


def cmd_antmill(a) -> int:
    findings = find_loops(read_changes(a.repo, a.limit), a.min_flips)
    if a.json:
        print(json.dumps(to_dicts(findings), indent=2))
    elif not findings:
        print("no loops detected")
    else:
        for f in findings:
            print(f"{f.kind.upper():9} {f.path}  flips={f.flips}  agents={', '.join(f.agents)}  commits={' '.join(f.commits)}")
    return 1 if (findings and a.fail_on_loop) else 0


@_writes
def cmd_claim(a) -> int:
    agent = a.agent or os.environ.get("COLONY_AGENT", "unknown")
    print(claims.add(a.repo, a.text, a.check, agent))
    return 0


def cmd_verify(a) -> int:
    print(json.dumps(claims.verify_all(a.repo, a.allow_cmd)))
    return 0


def _agent(a) -> str:
    return a.agent or os.environ.get("COLONY_AGENT", "unknown")


@_writes
def cmd_lesson_add(a) -> int:
    print(claims.add(a.repo, a.text, a.check, _agent(a), kind="lesson", paths=a.path or []))
    return 0


def cmd_lesson_find(a) -> int:
    hits = claims.lessons_for(a.repo, a.path or None, a.query or "", a.all)
    for c in hits:
        print(brief.line(c))
    if not hits:
        print("no lessons found")
    return 0


@_writes
def cmd_review(a) -> int:
    try:
        claims.review(a.repo, a.claim_id, a.verdict, _agent(a), a.family)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("recorded")
    return 0


def cmd_freeze(a) -> int:
    claims.freeze(a.repo)
    print("frozen: agents can no longer add claims, lessons or reviews. `colony thaw` to resume.")
    return 0


def cmd_thaw(a) -> int:
    claims.thaw(a.repo)
    print("thawed")
    return 0


def cmd_quarantine(a) -> int:
    try:
        claims.quarantine(a.repo, a.claim_id, a.reason or "", "human")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("quarantined (kept in the log, hidden from agents)")
    return 0


def cmd_release(a) -> int:
    try:
        claims.release(a.repo, a.claim_id)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("released")
    return 0


def cmd_reset(a) -> int:
    plan = guard.reset_plan(a.repo, a.loops_only)
    for c in plan:
        print(brief.line(c))
    if not plan:
        print("nothing to quarantine")
    elif a.yes:
        n = guard.apply_reset(a.repo, plan, a.reason or "reset")
        print(f"quarantined {n} claim(s). Verified claims were kept as the baseline.")
    else:
        print(f"\n{len(plan)} claim(s) would be quarantined. Re-run with --yes to apply.")
    return 0


def cmd_ledger(a) -> int:
    table = ledger.build(a.repo, a.limit)
    print(json.dumps(table, indent=2) if a.json else ledger.render(table))
    return 0


def cmd_brief(a) -> int:
    sys.stdout.write(brief.build(a.repo))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="colony", description=__doc__)
    p.add_argument("--repo", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create .colony/ and install the commit-attribution hook").set_defaults(fn=cmd_init)
    s = sub.add_parser("antmill", help="detect agents undoing each other's work")
    s.add_argument("--limit", type=int, default=500)
    s.add_argument("--min-flips", type=int, default=2)
    s.add_argument("--json", action="store_true")
    s.add_argument("--fail-on-loop", action="store_true")
    s.set_defaults(fn=cmd_antmill)
    s = sub.add_parser("claim", help="record a note other agents may rely on")
    s.add_argument("text")
    s.add_argument("--check", help="file:<path> | grep:<regex>::<path> | commit:<sha> | cmd:<command>")
    s.add_argument("--agent")
    s.set_defaults(fn=cmd_claim)
    s = sub.add_parser("verify", help="run claim checks")
    s.add_argument("--allow-cmd", action="store_true", help="also run cmd: checks (they execute shell commands)")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("lesson", help="share what you learned (failure -> fix) with every agent")
    ls = s.add_subparsers(dest="lcmd", required=True)
    x = ls.add_parser("add")
    x.add_argument("text")
    x.add_argument("--path", action="append", help="file or folder this lesson applies to (repeatable)")
    x.add_argument("--check", help="evidence, e.g. commit:<sha> or grep:<regex>::<path>")
    x.add_argument("--agent")
    x.set_defaults(fn=cmd_lesson_add)
    x = ls.add_parser("find", help="lessons relevant to files you are about to touch")
    x.add_argument("--path", action="append")
    x.add_argument("--query")
    x.add_argument("--all", action="store_true", help="include contradicted lessons")
    x.set_defaults(fn=cmd_lesson_find)
    s = sub.add_parser("review", help="give an independent verdict on another agent's claim")
    s.add_argument("claim_id")
    s.add_argument("--verdict", required=True, choices=["agree", "disagree"])
    s.add_argument("--agent")
    s.add_argument("--family", help="model family override (default: inferred from agent name)")
    s.set_defaults(fn=cmd_review)
    sub.add_parser("freeze", help="pause all shared writes (kill switch)").set_defaults(fn=cmd_freeze)
    sub.add_parser("thaw", help="resume shared writes").set_defaults(fn=cmd_thaw)
    s = sub.add_parser("quarantine", help="set one claim aside (never deleted)")
    s.add_argument("claim_id")
    s.add_argument("--reason")
    s.set_defaults(fn=cmd_quarantine)
    s = sub.add_parser("release", help="bring a quarantined claim back")
    s.add_argument("claim_id")
    s.set_defaults(fn=cmd_release)
    s = sub.add_parser("reset", help="quarantine everything not verified (or only what touches looping files)")
    s.add_argument("--loops-only", action="store_true")
    s.add_argument("--reason")
    s.add_argument("--yes", action="store_true", help="apply; without it, only shows the plan")
    s.set_defaults(fn=cmd_reset)
    s = sub.add_parser("ledger", help="per-agent track record from git and checks")
    s.add_argument("--limit", type=int, default=500)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_ledger)
    sub.add_parser("brief", help="print the briefing for an agent").set_defaults(fn=cmd_brief)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
