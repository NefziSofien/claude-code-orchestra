import unittest

from orchid.config import parse_config
from tests.helpers import remove, write_config


class ParseConfigTests(unittest.TestCase):
    def test_defaults_and_overrides(self):
        path = write_config("# c\nname = demo\ndebug = true\nretries = 5\n")
        self.addCleanup(remove, path)
        cfg = parse_config(path)
        self.assertEqual(cfg["name"], "demo")
        self.assertTrue(cfg["debug"])
        self.assertEqual(cfg["retries"], 5)
        self.assertEqual(cfg["cache_dir"], "/tmp/orchid")

    def test_unknown_key(self):
        path = write_config("bogus = 1\n")
        self.addCleanup(remove, path)
        with self.assertRaises(KeyError):
            parse_config(path)


if __name__ == "__main__":
    unittest.main()
