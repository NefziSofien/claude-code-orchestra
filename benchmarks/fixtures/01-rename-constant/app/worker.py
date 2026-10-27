"""Job worker with a retry budget per job."""
from app.settings import MAX_RETRIES


class Job:
    def __init__(self, name):
        self.name = name
        self.attempts = 0

    def can_retry(self):
        return self.attempts < MAX_RETRIES


def run(job, action):
    while True:
        job.attempts += 1
        if action():
            return True
        if not job.can_retry():
            return False
