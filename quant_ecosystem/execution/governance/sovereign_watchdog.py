from quant_ecosystem.execution.execution_audit import (
    load_execution_events,
)


WATCH_STATES = {
    "UNCERTAIN",
    "DEADLETTER",
    "CANCEL_PENDING",
    "RECONCILING",
}


class SovereignWatchdog:
    """
    Autonomous operational governance loop.
    """

    def __init__(
        self,
        execution_metrics=None,
    ):
        self._metrics = execution_metrics

    def scan(self):
        incidents = []

        events = load_execution_events()

        for event in events:
            state = str(
                event.get(
                    "lifecycle_state",
                    ""
                )
            ).upper().strip()

            if state in WATCH_STATES:
                incidents.append(event)

                if self._metrics:
                    self._metrics.record_watchdog_incident()

        return incidents