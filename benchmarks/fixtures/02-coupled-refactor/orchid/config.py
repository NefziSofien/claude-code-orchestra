"""Config file parsing: `key = value` lines, `#` comments."""

DEFAULTS = {"name": "orchid", "debug": False, "retries": 3, "cache_dir": "/tmp/orchid"}


def _coerce(key, raw):
    if isinstance(DEFAULTS[key], bool):
        return raw.lower() in ("1", "true", "yes")
    if isinstance(DEFAULTS[key], int):
        return int(raw)
    return raw


def parse_config(path):
    """Read the file at `path` and return the settings as a dict."""
    result = dict(DEFAULTS)
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, raw = line.partition("=")
            key = key.strip()
            if key not in DEFAULTS:
                raise KeyError(f"unknown config key: {key}")
            result[key] = _coerce(key, raw.strip())
    return result
