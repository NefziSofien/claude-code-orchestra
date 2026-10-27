"""Scheduler that computes the backoff plan."""
from app.settings import MAX_RETRIES


def backoff_plan(base=1):
    return [base * 2**i for i in range(MAX_RETRIES)]
