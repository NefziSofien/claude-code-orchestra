import unittest

from app.client import call_with_retry
from app.scheduler import backoff_plan
from app.settings import MAX_RETRIES
from app.worker import Job, run


class RetryTests(unittest.TestCase):
    def test_client_succeeds_after_failures(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < MAX_RETRIES:
                raise RuntimeError("boom")
            return "ok"

        self.assertEqual(call_with_retry(fn), "ok")

    def test_client_gives_up(self):
        def fn():
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            call_with_retry(fn)

    def test_worker_stops_at_limit(self):
        job = Job("x")
        self.assertFalse(run(job, lambda: False))
        self.assertEqual(job.attempts, MAX_RETRIES)

    def test_backoff_length(self):
        self.assertEqual(len(backoff_plan()), MAX_RETRIES)


if __name__ == "__main__":
    unittest.main()
