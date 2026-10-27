"""A flaky-call client that retries a bounded number of times."""
from app.settings import MAX_RETRIES


def call_with_retry(fn):
    last = None
    for _ in range(MAX_RETRIES):
        try:
            return fn()
        except RuntimeError as exc:
            last = exc
    raise RuntimeError(f"gave up after {MAX_RETRIES} attempts") from last
