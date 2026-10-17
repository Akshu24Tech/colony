import unittest
from pathlib import Path

from colony import claims, guard, ledger
from test_colony import commit, new_repo


def pingpong_repo():
    d = new_repo()
    Path(d, "src").mkdir()
    for i, (text, who) in enumerate([("A", "claude-code"), ("B", "gemini-cli"), ("A", "claude-code"), ("B", "gemini-cli")]):
        commit(d, "src/f.txt", text, who, f"edit {i}")
    return d


def status(d, cid):
    return next(c["status"] for c in claims.current(d) if c["id"] == cid)


class Freeze(unittest.TestCase):
    def test_freeze_blocks_agent_writes_not_human_actions(self):
        d = new_repo()
        cid = claims.add(d, "a fact", "file:x", "claude-code")
        claims.freeze(d)
        with self.assertRaises(claims.Frozen):
            claims.add(d, "another", None, "gemini-cli")
        with self.assertRaises(claims.Frozen):
            claims.review(d, cid, "agree", "gemini-cli")
        claims.verify_all(d)                    # human actions still work
        claims.quarantine(d, cid, "test")
        claims.thaw(d)
        claims.add(d, "now allowed", None, "gemini-cli")


class Quarantine(unittest.TestCase):
    def test_hidden_but_never_deleted_and_releasable(self):
        d = new_repo()
        cid = claims.add(d, "lesson", None, "claude-code", "lesson", ["src/a.py"])
        claims.quarantine(d, cid, "suspicious")
        self.assertEqual(status(d, cid), "quarantined")
        self.assertEqual(claims.lessons_for(d, ["src/a.py"]), [])
        self.assertEqual(len(claims.lessons_for(d, ["src/a.py"], include_contradicted=True)), 1)
        claims.release(d, cid)
        self.assertEqual(status(d, cid), "unverified")
        self.assertEqual(len(claims.events(d)), 3)  # claim, quarantine, release: history intact

    def test_unknown_claim_rejected(self):
        with self.assertRaises(ValueError):
            claims.quarantine(new_repo(), "nope")


class Reset(unittest.TestCase):
    def setUp(self):
        self.d = pingpong_repo()
        self.looping = claims.add(self.d, "looping-file lesson", None, "claude-code", "lesson", ["src/f.txt"])
        self.other = claims.add(self.d, "docs lesson", None, "claude-code", "lesson", ["docs"])
        self.baseline = claims.add(self.d, "src exists", "file:src", "claude-code", "fact", ["src/f.txt"])
        claims.verify_all(self.d)

    def test_loops_only_touches_only_the_looping_region(self):
        plan = guard.reset_plan(self.d, loops_only=True)
        self.assertEqual([c["id"] for c in plan], [self.looping])
        guard.apply_reset(self.d, plan, "antmill")
        self.assertEqual(status(self.d, self.looping), "quarantined")
        self.assertEqual(status(self.d, self.other), "unverified")
        self.assertEqual(status(self.d, self.baseline), "verified")

    def test_full_reset_keeps_verified_baseline(self):
        guard.apply_reset(self.d, guard.reset_plan(self.d), "reset")
        self.assertEqual(status(self.d, self.baseline), "verified")
        self.assertEqual(status(self.d, self.looping), "quarantined")
        self.assertEqual(status(self.d, self.other), "quarantined")


class Ledger(unittest.TestCase):
    def test_counts_from_evidence(self):
        d = pingpong_repo()
        Path(d, "app.py").write_text("x = 1\n")
        bad = claims.add(d, "app has retries", "grep:retry::app.py", "claude-code")
        good = claims.add(d, "app exists", "file:app.py", "claude-code")
        claims.review(d, bad, "agree", "gemini-cli")      # wrong: claim fails its check
        claims.review(d, bad, "disagree", "codex")        # right
        claims.review(d, good, "agree", "codex")          # right
        claims.verify_all(d)
        t = ledger.build(d)
        self.assertEqual(t["claude-code"]["undone_by_other"], 1)
        self.assertEqual(t["claude-code"]["undid_other"], 1)
        self.assertEqual((t["claude-code"]["claims_verified"], t["claude-code"]["claims_failed"]), (1, 1))
        self.assertEqual((t["gemini-cli"]["reviews_right"], t["gemini-cli"]["reviews_wrong"]), (0, 1))
        self.assertEqual((t["codex"]["reviews_right"], t["codex"]["reviews_wrong"]), (2, 0))
        self.assertIn("claude-code", ledger.render(t))


if __name__ == "__main__":
    unittest.main()
