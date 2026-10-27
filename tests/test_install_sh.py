import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL = os.path.abspath(os.path.join(HERE, "..", "install.sh"))
BASH = shutil.which("bash")


def snapshot(root):
    return sorted(os.path.relpath(os.path.join(d, n), root) for d, ds, fs in os.walk(root) for n in ds + fs)


@unittest.skipUnless(BASH and os.name != "nt", "install.sh needs bash on a POSIX system")
class InstallShTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.join(self.tmp.name, "home")
        self.claude = os.path.join(self.tmp.name, "claude")
        os.makedirs(self.home)
        self.skill = os.path.join(self.claude, "skills", "orchestrate", "SKILL.md")

    def install(self, *args):
        env = dict(os.environ, HOME=self.home, CLAUDE_CONFIG_DIR=self.claude)
        r = subprocess.run([BASH, INSTALL, "--no-cursor", *args], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_dry_run_changes_nothing(self):
        out = self.install("--dry-run")
        self.assertIn("[dry-run]", out)
        self.assertFalse(os.path.exists(self.claude))
        self.assertEqual(snapshot(self.home), [])

    def test_copy_then_second_run_is_noop(self):
        self.install("--copy")
        self.assertTrue(os.path.isfile(self.skill) and not os.path.islink(self.skill))
        before = snapshot(self.claude)
        out = self.install("--copy")
        self.assertEqual(snapshot(self.claude), before)
        self.assertNotIn("backup", out)
        self.assertIn("already up to date", out)

    def test_copy_replaces_changed_file_with_backup(self):
        self.install("--copy")
        with open(self.skill, "w", encoding="utf-8") as f:
            f.write("local edit\n")
        out = self.install("--copy")
        self.assertIn("backup", out)
        backups = [n for n in os.listdir(os.path.dirname(self.skill)) if ".bak-" in n]
        self.assertEqual(len(backups), 1)
        with open(os.path.join(os.path.dirname(self.skill), backups[0]), encoding="utf-8") as f:
            self.assertEqual(f.read(), "local edit\n")

    def test_link_mode_second_run_is_noop(self):
        self.install()
        self.assertTrue(os.path.islink(self.skill))
        out = self.install()
        self.assertIn("already linked", out)
        self.assertNotIn("backup", out)

    def test_unknown_option_fails(self):
        env = dict(os.environ, HOME=self.home, CLAUDE_CONFIG_DIR=self.claude)
        r = subprocess.run([BASH, INSTALL, "--bogus"], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
