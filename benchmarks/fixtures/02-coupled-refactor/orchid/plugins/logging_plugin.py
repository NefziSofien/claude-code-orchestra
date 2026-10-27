"""Logging plugin."""
from orchid.config import parse_config


def setup(cfg):
    level = "DEBUG" if cfg["debug"] else "INFO"
    return f"logging:{cfg['name']}:{level}"


def setup_from_file(path):
    return setup(parse_config(path))
