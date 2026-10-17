#!/usr/bin/env python3
"""Evaluation harness: does shared, evidence-checked state beat the alternatives?

Arms:  alone   no notes
       notes   a hand-written AGENTS.md holding the same note
       colony  the note recorded in Colony with its check run (false notes become DO NOT TRUST)
Each run: fresh git repo -> your agent command -> success check on the final repo state.

  python eval/run_eval.py --agent-cmd 'python3 {root}/eval/mock_agent.py {prompt}'   # plumbing test only
  python eval/run_eval.py --agent-cmd 'your-agent-cli -p {prompt}' --repeats 5       # a real run

{prompt} is shell-quoted for you, {root} is the Colony repo path. The agent runs inside a temp git repo,
but it is YOUR agent with YOUR permissions: run real agents in a sandbox or container.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from colony import claims  # noqa: E402

ARMS = ("alone", "notes", "colony")
INSTRUCTION = {
    "alone": "{task}",
    "notes": "Read AGENTS.md before starting. Then: {task}",
    # the same text as docs/AGENTS-snippet.md, i.e. the fallback instruction Colony ships
    "colony": ("Before starting work, run `colony brief` and read it. Do not rely on claims marked "
               "DO NOT TRUST. Then: {task}"),
}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=seed", "-c", "user.email=s@x", *args],
                   check=True, capture_output=True)


def build_repo(task: dict, arm: str, base: Path) -> Path:
    repo = base / "repo"
    repo.mkdir()
    for rel, text in task["files"].items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    if arm == "notes":
        (repo / "AGENTS.md").write_text("# Project notes\n\n- " + task["note"] + "\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "seed")
    if arm == "colony":
        claims.add(str(repo), task["note"], task["note_check"], "seed-agent", "lesson", task["note_paths"])
        claims.verify_all(str(repo))
    return repo


def make_env(base: Path, task_id: str) -> dict:
    bin_dir = base / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "colony"
    shim.write_text(f'#!/bin/sh\nPYTHONPATH="{ROOT / "src"}" exec "{sys.executable}" -m colony.cli "$@"\n')
    shim.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "EVAL_TASK": task_id,
            "COLONY_AGENT": "eval-agent"}


def run_one(task: dict, arm: str, cmd_tpl: str, timeout: int, keep: bool) -> dict:
    base = Path(tempfile.mkdtemp(prefix="colony-eval-"))
    try:
        repo = build_repo(task, arm, base)
        prompt = INSTRUCTION[arm].format(task=task["task"])
        cmd = cmd_tpl.replace("{root}", str(ROOT)).replace("{prompt}", shlex.quote(prompt))
        t0 = time.time()
        try:
            r = subprocess.run(cmd, shell=True, cwd=repo, env=make_env(base, task["id"]),
                               capture_output=True, text=True, timeout=timeout)
            code, tail = r.returncode, (r.stdout + r.stderr)[-300:]
        except subprocess.TimeoutExpired:
            code, tail = -1, "timeout"
        ok = subprocess.run(task["success_check"], shell=True, cwd=repo, capture_output=True).returncode == 0
        return {"task": task["id"], "type": task["type"], "arm": arm, "passed": ok,
                "seconds": round(time.time() - t0, 1), "agent_exit": code, "agent_tail": tail}
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


def summarize(rows: list[dict], arms: list[str]) -> str:
    cell = defaultdict(lambda: [0, 0])
    for r in rows:
        c = cell[(r["type"], r["arm"])]
        c[0] += r["passed"]
        c[1] += 1
    types = sorted({r["type"] for r in rows})
    out = ["type".ljust(14) + "".join(a.rjust(9) for a in arms)]
    for t in types:
        out.append(t.ljust(14) + "".join(f"{cell[(t, a)][0]}/{cell[(t, a)][1]}".rjust(9) for a in arms))
    out += ["", "Counts of runs whose final repo passed the success check. Small samples: report raw counts.",
            "true-lesson: does sharing a true lesson help?  false-note: does a wrong note hurt, and does Colony stop it?"]
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--agent-cmd", required=True)
    p.add_argument("--arms", default=",".join(ARMS))
    p.add_argument("--tasks", help="comma-separated task ids (default: all)")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--out", default="eval-results.jsonl")
    p.add_argument("--keep", action="store_true", help="keep temp repos for inspection")
    a = p.parse_args()
    tasks = json.loads((ROOT / "eval" / "tasks.json").read_text())
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    arms = a.arms.split(",")
    rows = []
    with open(a.out, "w") as f:
        for task in tasks:
            for arm in arms:
                for i in range(a.repeats):
                    row = {**run_one(task, arm, a.agent_cmd, a.timeout, a.keep), "repeat": i}
                    rows.append(row)
                    f.write(json.dumps(row) + "\n")
                    print(f"{task['id']:18} {arm:7} {'pass' if row['passed'] else 'FAIL'}  {row['seconds']}s", flush=True)
    print("\n" + summarize(rows, arms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
