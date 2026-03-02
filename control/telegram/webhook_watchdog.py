import time


class WebhookWatchdog:

    def __init__(self, timeout_sec=180):
        self.timeout_sec = max(30, int(timeout_sec))
        self.last_callback_ts = 0.0
        self.seen_callback = False
        self.failover_triggered = False

    def mark_callback(self):
        self.last_callback_ts = time.time()
        self.seen_callback = True
        self.failover_triggered = False

    def should_failover(self):
        if not self.seen_callback:
            return False
        if self.failover_triggered:
            return False
        elapsed = time.time() - self.last_callback_ts
        if elapsed >= self.timeout_sec:
            self.failover_triggered = True
            return True
        return False
