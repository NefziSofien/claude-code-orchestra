import io
import unittest
from contextlib import redirect_stdout

from orchid import cli
from orchid.loader import load
from orchid.plugins import cache, logging_plugin
from tests.helpers import remove, write_config


class LoaderPluginCliTests(unittest.TestCase):
    def setUp(self):
        self.path = write_config("name = demo\ndebug = yes\ncache_dir = /tmp/x\n")
        self.addCleanup(remove, self.path)

    def test_loader(self):
        cfg, active = load(self.path)
        self.assertEqual(cfg["name"], "demo")
        self.assertEqual(len(active), 2)

    def test_plugins(self):
        cfg, _ = load(self.path)
        self.assertEqual(logging_plugin.setup(cfg), "logging:demo:DEBUG")
        self.assertEqual(cache.setup(cfg), "cache:/tmp/x:retries=3")
        self.assertEqual(logging_plugin.setup_from_file(self.path), "logging:demo:DEBUG")

    def test_cli(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cli.main([self.path]), 0)
        self.assertTrue(out.getvalue().startswith("demo: "))

    def test_cli_usage(self):
        self.assertEqual(cli.main([]), 2)


if __name__ == "__main__":
    unittest.main()
