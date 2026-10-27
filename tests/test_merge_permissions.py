import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "lean-ctx", "merge_permissions.py")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


WANTED = json.loads(read(os.path.join(HERE, "..", "lean-ctx", "claude-permissions.json")))["permissions"]


def merge(target, *flags):
    return subprocess.run([sys.executable, SCRIPT, target, *flags], capture_output=True, text=True)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class MergePermissionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = os.path.join(self.tmp.name, "sub", "settings.json")

    def backups(self):
        d = os.path.dirname(self.target)
        return [n for n in os.listdir(d) if ".bak-" in n] if os.path.isdir(d) else []

    def test_missing_file_is_created(self):
        r = merge(self.target)
        self.assertEqual(r.returncode, 0, r.stderr)
        perms = load(self.target)["permissions"]
        for key in ("allow", "ask", "deny"):
            for entry in WANTED.get(key, []):
                self.assertIn(entry, perms[key])
        self.assertEqual(self.backups(), [])

    def test_idempotent(self):
        merge(self.target)
        first = read(self.target)
        r = merge(self.target)
        self.assertEqual(r.returncode, 0)
        self.assertIn("already has", r.stdout)
        self.assertEqual(read(self.target), first)
        self.assertEqual(self.backups(), [])

    def test_preserves_existing_settings_and_backs_up(self):
        os.makedirs(os.path.dirname(self.target))
        original = {"model": "opus", "permissions": {"allow": ["Bash(ls:*)"], "defaultMode": "plan"}, "env": {"A": "1"}}
        with open(self.target, "w", encoding="utf-8") as f:
            json.dump(original, f)
        r = merge(self.target)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = load(self.target)
        self.assertEqual(data["model"], "opus")
        self.assertEqual(data["env"], {"A": "1"})
        self.assertEqual(data["permissions"]["defaultMode"], "plan")
        self.assertIn("Bash(ls:*)", data["permissions"]["allow"])
        self.assertEqual(len(self.backups()), 1)

    def test_ask_entry_removed_from_allow(self):
        if not WANTED.get("ask"):
            self.skipTest("no ask entries configured")
        entry = WANTED["ask"][0]
        os.makedirs(os.path.dirname(self.target))
        with open(self.target, "w", encoding="utf-8") as f:
            json.dump({"permissions": {"allow": [entry]}}, f)
        merge(self.target)
        perms = load(self.target)["permissions"]
        self.assertNotIn(entry, perms["allow"])
        self.assertIn(entry, perms["ask"])

    def test_dry_run_changes_nothing(self):
        r = merge(self.target, "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("[dry-run]", r.stdout)
        self.assertFalse(os.path.exists(self.target))

    def test_empty_file_is_treated_as_empty_settings(self):
        os.makedirs(os.path.dirname(self.target))
        open(self.target, "w").close()
        self.assertEqual(merge(self.target).returncode, 0)
        self.assertIn("permissions", load(self.target))

    def test_usage_without_args(self):
        r = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
