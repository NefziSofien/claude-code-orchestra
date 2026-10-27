import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = load("orchestra_validate", "tools/orchestra-validate.py")
REPORT = os.path.join(ROOT, "hooks", "subagent-report-check.py")
SCOPE = os.path.join(ROOT, "hooks", "scope-guard.py")

GOOD = """# Task: demo
Updated: 2026-10-27T10:00:00
Wave: 1/2

## Units
| id | goal | worker | vehicle/model | status | branch/worktree |
|----|------|--------|---------------|--------|-----------------|
| U1 | a | implementer | subagent/sonnet | running | b1 |
| U2 | b | implementer | subagent/sonnet | done | b1 |

## Decisions
- x

## Open questions
- y

## Next
- z
"""

ROWS = ("| U1 | a | implementer | subagent/sonnet | running | b1 |\n"
        "| U2 | b | implementer | subagent/sonnet | done | b1 |\n")


def run(script, payload, env=None):
    e = dict(os.environ)
    e.pop("ORCHESTRA_SCOPE", None)
    e.update(env or {})
    p = subprocess.run([sys.executable, script], input=json.dumps(payload),
                       capture_output=True, text=True, env=e)
    return p.returncode, p.stdout


class ValidateTests(unittest.TestCase):
    def test_good(self):
        self.assertEqual(V.validate(GOOD), [])

    def test_bad_wave(self):
        self.assertTrue(V.validate(GOOD.replace("Wave: 1/2", "Wave: x")))

    def test_missing_section(self):
        self.assertTrue(V.validate(GOOD.replace("## Next\n- z\n", "")))

    def test_duplicate_id(self):
        bad = GOOD.replace("| U2 |", "| U1 |")
        self.assertTrue(any("duplicate unit id" in p for p in V.validate(bad)))

    def test_shared_branch_non_done(self):
        bad = GOOD.replace("| done |", "| pending |")
        self.assertTrue(any("share branch" in p for p in V.validate(bad)))

    def test_too_many_running(self):
        rows = "".join("| U%d | g | w | v | running | b%d |\n" % (i, i) for i in range(5))
        bad = GOOD.replace(ROWS, rows)
        self.assertTrue(any("at once" in p for p in V.validate(bad)))

    def test_non_bullet(self):
        self.assertTrue(V.validate(GOOD.replace("- x", "x")))

    def test_repo_state_and_corrupted_copy(self):
        path = os.path.join(ROOT, ".orchestra", "state.md")
        if not os.path.exists(path):
            self.skipTest("no .orchestra/state.md (gitignored)")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(V.validate(text), [])
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as t:
            t.write(text.replace("## Units", "## Unitz"))
        try:
            self.assertEqual(V.main(["x", t.name]), 1)
        finally:
            os.unlink(t.name)


class ReportHookTests(unittest.TestCase):
    OK = "STATUS: done\nCHANGED: a\nDECISIONS: -\nOPEN: -\nVERIFIED: ok"

    def test_ok(self):
        self.assertEqual(run(REPORT, {"last_assistant_message": self.OK}), (0, ""))

    def test_missing_field_blocks(self):
        _, out = run(REPORT, {"last_assistant_message": "STATUS: done"})
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_too_long_blocks(self):
        _, out = run(REPORT, {"last_assistant_message": self.OK + "\ny" * 6})
        self.assertIn("lines", json.loads(out)["reason"])

    def test_stop_hook_active_allows(self):
        self.assertEqual(run(REPORT, {"stop_hook_active": True, "last_assistant_message": ""}), (0, ""))


class ScopeHookTests(unittest.TestCase):
    def call(self, path, scope):
        return run(SCOPE, {"cwd": "/r", "tool_name": "Write", "tool_input": {"file_path": path}},
                   {"ORCHESTRA_SCOPE": scope} if scope is not None else None)

    def test_unset_allows(self):
        self.assertEqual(self.call("/etc/x", None), (0, ""))

    def test_inside_allowed(self):
        self.assertEqual(self.call("/r/tools/a.py", "tools/*:hooks/*"), (0, ""))

    def test_outside_denied(self):
        _, out = self.call("/r/src/a.py", "tools/*:hooks/*")
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
