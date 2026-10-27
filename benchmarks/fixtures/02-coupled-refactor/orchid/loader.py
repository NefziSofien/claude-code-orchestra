"""Loads config and enables the plugins it asks for."""
from orchid.config import parse_config
from orchid.plugins import cache, logging_plugin


def load(path):
    cfg = parse_config(path)
    active = [logging_plugin.setup(cfg)]
    if cfg["cache_dir"]:
        active.append(cache.setup(cfg))
    return cfg, active
