from quant_ecosystem.execution.execution_audit import (
    load_execution_events,
)


RETRYABLE_FAILURES = {
    "TIMEOUT",
    "NETWORK",
    "DISCONNECT",
    "TEMPORARY",
}


class DeadLetterRecovery:

    def __init__(
        self,
        execution_metrics=None,
    ):
        self._metrics = execution_metrics

    def recover_deadletters(self):
        recovered = []

        events = load_execution_events()

        for event in events:
            state = str(
                event.get(
                    "lifecycle_state",
                    ""
                )
            ).upper().strip()

            if state != "DEADLETTER":
                continue

            reason = self.classify_failure(
                event
            )

            if self.is_retryable(reason):
                recovered.append(event)

                if self._metrics:
                    self._metrics.record_recovered()

        return recovered

    def classify_failure(
        self,
        event,
    ):
        payload = str(event).upper()

        if "TIMEOUT" in payload:
            return "TIMEOUT"

        if "DISCONNECT" in payload:
            return "DISCONNECT"

        if "NETWORK" in payload:
            return "NETWORK"

        return "PERMANENT"

    def is_retryable(
        self,
        reason,
    ):
        return reason in RETRYABLE_FAILURES