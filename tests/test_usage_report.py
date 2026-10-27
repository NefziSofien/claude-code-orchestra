import contextlib
import importlib.util
import io
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures", "projects")

spec = importlib.util.spec_from_file_location(
    "usage_report", os.path.join(HERE, "..", "tools", "usage-report.py"))
ur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ur)


def run_cli(*argv):
    import sys
    out, err = io.StringIO(), io.StringIO()
    old = sys.argv
    sys.argv = ["usage-report.py", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ur.main()
    finally:
        sys.argv = old
    return code, out.getvalue(), err.getvalue()


class HelperTests(unittest.TestCase):
    def test_fmt(self):
        self.assertEqual(ur.fmt(999), "999")
        self.assertEqual(ur.fmt(1500), "1.5k")
        self.assertEqual(ur.fmt(2_000_000), "2.0M")

    def test_command_heads(self):
        self.assertEqual(ur.command_heads("cd /x && git status | head; npm test"),
                         ["git status", "head", "npm test"])
        self.assertEqual(ur.command_heads("FOO=1 sudo ls -la"), ["ls"])
        self.assertEqual(ur.command_heads("cat <<EOF\nrm -rf x\nEOF"), ["cat"])

    def test_project_name(self):
        self.assertEqual(ur.project_name("-home-alice-code-my-app"), "code-my-app")
        self.assertEqual(ur.project_name("C--Users-alice-code-my-app"), "code-my-app")
        self.assertLessEqual(len(ur.project_name("x" * 100)), 48)


class AggregateTests(unittest.TestCase):
    def setUp(self):
        files = ur.find_transcripts(FIXTURES)
        self.stats = ur.aggregate(files, FIXTURES, None)

    def test_requests_counted_once_and_synthetic_skipped(self):
        self.assertEqual(set(self.stats.per_model), {"claude-opus-4", "claude-haiku-4"})
        self.assertEqual(self.stats.per_model["claude-opus-4"]["requests"], 1)
        self.assertEqual(self.stats.per_model["claude-opus-4"]["output_tokens"], 500)

    def test_tools_and_breakdowns(self):
        self.assertEqual(self.stats.mcp_servers, {"lean-ctx": 1})
        self.assertEqual(self.stats.skills, {"orchestrate": 1})
        self.assertEqual(self.stats.agents, {"explorer (haiku)": 1})
        self.assertEqual(self.stats.bash["git status"], 1)

    def test_sidechain_and_summary(self):
        self.assertEqual(self.stats.sidechain_out, 100)
        prompt, cache_rate, out_total = ur.summarize(self.stats)
        self.assertEqual(prompt, 3150)
        self.assertEqual(out_total, 600)
        self.assertAlmostEqual(cache_rate, 2000 / 3150)
        self.assertEqual(self.stats.per_project["code-my-app"], 3750)

    def test_since_filters_old_records(self):
        from datetime import datetime, timezone
        files = ur.find_transcripts(FIXTURES)
        stats = ur.aggregate(files, FIXTURES, datetime(2030, 1, 1, tzinfo=timezone.utc))
        self.assertFalse(stats.per_model)


class CliTests(unittest.TestCase):
    def test_text_report(self):
        code, out, _ = run_cli("--days", "0", "--projects-dir", FIXTURES)
        self.assertEqual(code, 0)
        self.assertIn("Claude Code usage, all time: 1 sessions, 1 transcript files", out)
        self.assertIn("Cache read rate: 63%", out)
        self.assertIn("Subagents: 17% of output tokens", out)
        self.assertIn("Suggestions", out)

    def test_json_report(self):
        code, out, _ = run_cli("--days", "0", "--json", "--projects-dir", FIXTURES)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["sessions"], 1)
        self.assertEqual(data["models"]["claude-haiku-4"]["cache_read_input_tokens"], 2000)

    def test_no_transcripts(self):
        code, _, err = run_cli("--projects-dir", os.path.join(HERE, "fixtures", "missing"))
        self.assertEqual(code, 1)
        self.assertIn("No transcripts found", err)


if __name__ == "__main__":
    unittest.main()
