"""Cache plugin."""


def setup(cfg):
    return f"cache:{cfg['cache_dir']}:retries={cfg['retries']}"
