"""Bound repeated native-worker restart attempts without retaining input data."""
from __future__ import annotations

import math

INITIAL_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 60


class WorkerRecovery:
    """Called under the worker's admission lock; only snapshots are read outside."""

    def __init__(self, clock):
        self.clock = clock
        self.consecutive_failures = 0
        self.retry_at = 0.0

    def remaining(self):
        return max(0, math.ceil(self.retry_at - self.clock()))

    def failed(self):
        # Saturate the counter: no unbounded integers or exponentiation.
        self.consecutive_failures = min(self.consecutive_failures + 1, 5)
        delay = min(MAX_BACKOFF_SECONDS,
                    INITIAL_BACKOFF_SECONDS * 2 ** (self.consecutive_failures - 1))
        self.retry_at = self.clock() + delay
        return delay

    def succeeded(self):
        self.consecutive_failures = 0
        self.retry_at = 0.0

    def snapshot(self):
        remaining = self.remaining()
        return {"cooldown": remaining > 0, "retry_after_seconds": remaining,
                "consecutive_failures": self.consecutive_failures}
