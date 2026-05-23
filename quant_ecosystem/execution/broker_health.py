from datetime import datetime


class BrokerHealth:
    """
    Tracks broker health state for execution resilience.
    """

    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.last_success = None
        self.last_latency = None

    def record_success(self, latency_ms=None):
        self.consecutive_failures = 0
        self.last_success = datetime.utcnow()
        self.last_latency = latency_ms

    def record_failure(self):
        self.consecutive_failures += 1

    def is_healthy(self):
        return self.consecutive_failures < self.failure_threshold