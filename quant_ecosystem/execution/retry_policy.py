import time
from collections import deque
from datetime import datetime, timedelta
import threading


TRANSIENT_KEYWORDS = (
    "timeout",
    "timed out",
    "connection reset",
    "temporarily unavailable",
    "rate limit",
    "429",
    "network",
)


FATAL_KEYWORDS = (
    "auth",
    "authentication",
    "invalid symbol",
    "insufficient funds",
    "rejected",
    "not allowed",
)


def is_transient_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in TRANSIENT_KEYWORDS)


def is_fatal_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in FATAL_KEYWORDS)



class CircuitBreakerOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(
        self,
        threshold=3,
        window_seconds=60,
        cooldown_seconds=300,
    ):
        self.threshold = threshold
        self.window = timedelta(seconds=window_seconds)
        self.cooldown = timedelta(seconds=cooldown_seconds)

        self.failures = deque()
        self.locked_until = None
        self.last_failure_reason = None

        self._lock = threading.Lock()

    def _prune(self, now):
        while self.failures and now - self.failures[0] > self.window:
            self.failures.popleft()

    def check(self):
        with self._lock:
            now = datetime.utcnow()

            self._prune(now)

            if self.locked_until:
                if now >= self.locked_until:
                    self.locked_until = None
                    self.failures.clear()
                else:
                    remaining = int(
                        (self.locked_until - now).total_seconds()
                    )
                    raise CircuitBreakerOpenError(
                        f"LIVE CIRCUIT BREAKER ACTIVE ({remaining}s remaining)"
                    )

    def record_failure(self, reason=None):
        with self._lock:
            now = datetime.utcnow()

            self._prune(now)
            self.failures.append(now)
            self.last_failure_reason = reason

            if len(self.failures) >= self.threshold:
                self.locked_until = now + self.cooldown

    def record_success(self):
        with self._lock:
            self.failures.clear()
            self.locked_until = None
            self.last_failure_reason = None

    def reset(self):
        self.record_success()

    def status(self):
        with self._lock:
            now = datetime.utcnow()
            self._prune(now)

            remaining = 0
            if self.locked_until and now < self.locked_until:
                remaining = int(
                    (self.locked_until - now).total_seconds()
                )

            return {
                "failure_count": len(self.failures),
                "locked": remaining > 0,
                "cooldown_remaining": remaining,
                "last_failure_reason": self.last_failure_reason,
            }


def execute_with_retry(fn, retries=3, base_delay=1.0):
    last_exc = None

    for attempt in range(retries):
        try:
            return fn()

        except Exception as exc:
            last_exc = exc

            if is_fatal_error(exc):
                raise

            if not is_transient_error(exc):
                raise

            if attempt == retries - 1:
                raise

            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

    raise last_exc