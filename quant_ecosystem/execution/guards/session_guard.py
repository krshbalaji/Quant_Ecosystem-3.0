import time


class SessionGuard:
    """
    Institutional broker session governance.
    Auth storm suppression + quarantine + telemetry.
    """

    def __init__(
        self,
        execution_metrics=None,
        cooldown_seconds=30,
        quarantine_failures=3,
    ):
        self._execution_metrics = execution_metrics
        self._cooldown_seconds = cooldown_seconds
        self._quarantine_failures = quarantine_failures
        self._broker_state = {}

    def _state(self, broker_name):
        if broker_name not in self._broker_state:
            self._broker_state[broker_name] = {
                "failures": 0,
                "last_attempt": 0,
                "quarantined": False,
            }
        return self._broker_state[broker_name]

    def ensure_live_session(
        self,
        broker,
        broker_name,
    ):
        state = self._state(broker_name)

        if state["quarantined"]:
            raise RuntimeError(
                f"BROKER QUARANTINED: {broker_name}"
            )

        if not hasattr(broker, "is_authenticated"):
            return

        if broker.is_authenticated():
            state["failures"] = 0
            return

        now = time.time()

        if (
            now - state["last_attempt"]
            < self._cooldown_seconds
        ):
            raise RuntimeError(
                f"AUTH COOLDOWN ACTIVE: {broker_name}"
            )

        state["last_attempt"] = now

        try:
            broker.authenticate()

            if broker.is_authenticated():
                state["failures"] = 0

                if self._execution_metrics:
                    self._execution_metrics.increment(
                        "broker_auth_success"
                    )

                return

        except Exception:
            pass

        try:
            broker.refresh_session()

            if broker.is_authenticated():
                state["failures"] = 0

                if self._execution_metrics:
                    self._execution_metrics.increment(
                        "broker_refresh_success"
                    )

                return

        except Exception:
            pass

        try:
            broker.invalidate_session()
        except Exception:
            pass

        state["failures"] += 1

        if self._execution_metrics:
            self._execution_metrics.increment(
                "broker_auth_failure"
            )

        if (
            state["failures"]
            >= self._quarantine_failures
        ):
            state["quarantined"] = True

            raise RuntimeError(
                f"BROKER QUARANTINED: {broker_name}"
            )

        raise RuntimeError(
            f"BROKER SESSION INVALID: {broker_name}"
        )

    def is_quarantined(
        self,
        broker_name,
    ):
        state = self._state(broker_name)
        return state["quarantined"]    