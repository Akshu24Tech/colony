import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from colony import claims
from colony.antmill import find_loops
from colony.gitlog import agent_of, read_changes


def sh(repo, *args, env=None):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True,
                   env={**os.environ, **(env or {})})


def commit(repo, path, text, agent, msg):
    Path(repo, path).write_text(text)
    sh(repo, "add", "-A")
    sh(repo, "-c", "user.name=dev", "-c", "user.email=d@x", "commit", "-m", f"{msg}\n\nAgent: {agent}")


def new_repo():
    d = tempfile.mkdtemp()
    sh(d, "init", "-q")
    return d


class AgentOf(unittest.TestCase):
    def test_trailer_beats_author(self):
        self.assertEqual(agent_of("dev", "fix\n\nAgent: gemini-cli"), "gemini-cli")

    def test_coauthor_then_author(self):
        self.assertEqual(agent_of("dev", "fix\n\nCo-authored-by: Claude <c@x>"), "Claude")
        self.assertEqual(agent_of("dev", "fix"), "dev")


class Antmill(unittest.TestCase):
    def test_pingpong_between_two_agents(self):
        d = new_repo()
        for i, (text, who) in enumerate([("A", "claude"), ("B", "gemini"), ("A", "claude"), ("B", "gemini")]):
            commit(d, "f.txt", text, who, f"edit {i}")
        found = find_loops(read_changes(d))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "pingpong")
        self.assertEqual(found[0].agents, ["claude", "gemini"])

    def test_single_agent_is_churn(self):
        d = new_repo()
        for i, text in enumerate(["A", "B", "A", "B"]):
            commit(d, "f.txt", text, "claude", f"edit {i}")
        self.assertEqual(find_loops(read_changes(d))[0].kind, "churn")

    def test_one_revert_is_not_a_loop(self):
        d = new_repo()
        for i, (text, who) in enumerate([("A", "claude"), ("B", "gemini"), ("A", "claude")]):
            commit(d, "f.txt", text, who, f"edit {i}")
        self.assertEqual(find_loops(read_changes(d)), [])

    def test_normal_progress_is_quiet(self):
        d = new_repo()
        for i, who in enumerate(["claude", "gemini", "claude", "gemini"]):
            commit(d, "f.txt", f"v{i}", who, f"edit {i}")
        self.assertEqual(find_loops(read_changes(d)), [])


class Claims(unittest.TestCase):
    def test_file_and_grep_checks(self):
        d = new_repo()
        Path(d, "app.py").write_text("PORT = 8080\n")
        claims.add(d, "app exists", "file:app.py", "a")
        claims.add(d, "port is 8080", r"grep:PORT = 8080::app.py", "a")
        claims.add(d, "port is 9000", r"grep:PORT = 9000::app.py", "b")
        claims.add(d, "no check", None, "b")
        counts = claims.verify_all(d)
        self.assertEqual(counts, {"verified": 2, "contradicted": 1, "skipped": 0})
        status = {c["text"]: c["status"] for c in claims.current(d)}
        self.assertEqual(status["port is 9000"], "contradicted")
        self.assertEqual(status["no check"], "unverified")

    def test_cmd_checks_need_opt_in(self):
        d = new_repo()
        claims.add(d, "tests pass", f"cmd:{sys.executable} -c pass", "a")
        self.assertEqual(claims.verify_all(d)["skipped"], 1)
        self.assertEqual(claims.verify_all(d, allow_cmd=True)["verified"], 1)


if __name__ == "__main__":
    unittest.main()


class Collective(unittest.TestCase):
    def _claim(self, d, agent="claude-code", check=None):
        return claims.add(d, "retries needed: API rate-limits", check, agent, kind="lesson", paths=["src/api.py"])

    def status(self, d, cid):
        return next(c["status"] for c in claims.current(d) if c["id"] == cid)

    def test_two_independent_families_corroborate(self):
        d = new_repo()
        cid = self._claim(d)
        claims.review(d, cid, "agree", "gemini-cli")
        self.assertEqual(self.status(d, cid), "unverified")  # one family is not enough
        claims.review(d, cid, "agree", "codex")
        self.assertEqual(self.status(d, cid), "corroborated")

    def test_same_family_and_unknown_do_not_count(self):
        d = new_repo()
        cid = self._claim(d)
        claims.review(d, cid, "agree", "claude-opus-second-session")
        claims.review(d, cid, "agree", "mystery-agent")
        claims.review(d, cid, "agree", "gemini-cli")
        self.assertEqual(self.status(d, cid), "unverified")

    def test_evidence_beats_agreement(self):
        d = new_repo()
        Path(d, "src").mkdir()
        Path(d, "src/api.py").write_text("x = 1\n")
        cid = self._claim(d, check="grep:retry::src/api.py")
        claims.review(d, cid, "agree", "gemini-cli")
        claims.review(d, cid, "agree", "codex")
        claims.verify_all(d)
        self.assertEqual(self.status(d, cid), "contradicted")

    def test_independent_disagreement_disputes(self):
        d = new_repo()
        cid = self._claim(d)
        claims.review(d, cid, "disagree", "gemini-cli")
        self.assertEqual(self.status(d, cid), "disputed")

    def test_cannot_review_own_claim(self):
        d = new_repo()
        cid = self._claim(d)
        with self.assertRaises(ValueError):
            claims.review(d, cid, "agree", "claude-code")

    def test_commit_evidence_and_lesson_lookup_by_path(self):
        d = new_repo()
        commit(d, "src.txt", "a", "claude", "fix rate limit")
        sha = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        good = claims.add(d, "fixed by backoff", f"commit:{sha}", "claude-code", "lesson", ["src/api.py"])
        bad = claims.add(d, "fixed by magic", "commit:deadbeef", "gemini-cli", "lesson", ["src/api.py"])
        claims.verify_all(d)
        self.assertEqual(self.status(d, good), "verified")
        self.assertEqual(self.status(d, bad), "contradicted")
        found = claims.lessons_for(d, ["src/api.py"])
        self.assertEqual([c["id"] for c in found], [good])          # contradicted hidden
        self.assertEqual(len(claims.lessons_for(d, ["src"])), 1)    # folder overlap
        self.assertEqual(claims.lessons_for(d, ["docs/readme.md"]), [])
