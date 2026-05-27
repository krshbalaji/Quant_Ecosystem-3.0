import threading
import time


class SessionGuard:
    """
    Institutional broker session governance
    with auth storm suppression.
    """

    COOLDOWN_SECONDS = 60
    FAILURE_THRESHOLD = 3

    def __init__(self):
        self._locks = {}
        self._failures = {}
        self._cooldowns = {}

    def ensure_live_session(
        self,
        broker,
        broker_name,
    ):
        if not hasattr(
            broker,
            "is_authenticated",
        ):
            return

        if broker.is_authenticated():
            self._reset_failures(
                broker_name
            )
            return

        if self._in_cooldown(
            broker_name
        ):
            raise RuntimeError(
                f"BROKER SESSION QUARANTINED: {broker_name}"
            )

        lock = self._get_lock(
            broker_name
        )

        with lock:
            if broker.is_authenticated():
                self._reset_failures(
                    broker_name
                )
                return

            try:
                broker.authenticate()

                if broker.is_authenticated():
                    self._reset_failures(
                        broker_name
                    )
                    return

            except Exception:
                pass

            try:
                broker.refresh_session()

                if broker.is_authenticated():
                    self._reset_failures(
                        broker_name
                    )
                    return

            except Exception:
                pass

            self._record_failure(
                broker_name
            )

            try:
                broker.invalidate_session()
            except Exception:
                pass

            raise RuntimeError(
                f"BROKER SESSION INVALID: {broker_name}"
            )

    def _get_lock(
        self,
        broker_name,
    ):
        if broker_name not in self._locks:
            self._locks[broker_name] = (
                threading.Lock()
            )

        return self._locks[
            broker_name
        ]

    def _record_failure(
        self,
        broker_name,
    ):
        count = self._failures.get(
            broker_name,
            0,
        ) + 1

        self._failures[
            broker_name
        ] = count

        if (
            count >=
            self.FAILURE_THRESHOLD
        ):
            self._cooldowns[
                broker_name
            ] = time.time()

    def _reset_failures(
        self,
        broker_name,
    ):
        self._failures.pop(
            broker_name,
            None,
        )

        self._cooldowns.pop(
            broker_name,
            None,
        )

    def _in_cooldown(
        self,
        broker_name,
    ):
        ts = self._cooldowns.get(
            broker_name
        )

        if not ts:
            return False

        if (
            time.time() - ts
            >
            self.COOLDOWN_SECONDS
        ):
            self._cooldowns.pop(
                broker_name,
                None,
            )
            return False

        return True

    def session_health(
        self,
        broker_name,
    ):
        return {
            "broker": broker_name,
            "failures": self._failures.get(
                broker_name,
                0,
            ),
            "quarantined": self._in_cooldown(
                broker_name
            ),
            "cooldown_remaining": self._cooldown_remaining(
                broker_name,
            ),
        }

    def is_quarantined(
        self,
        broker_name,
    ):
        return self._in_cooldown(
            broker_name
        )

    def _cooldown_remaining(
        self,
        broker_name,
    ):
        ts = self._cooldowns.get(
            broker_name
        )

        if not ts:
            return 0

        remaining = (
            self.COOLDOWN_SECONDS
            - (time.time() - ts)
        )

        return max(
            0,
            int(remaining),
        )