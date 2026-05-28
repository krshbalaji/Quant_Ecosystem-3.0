from quant_ecosystem.execution.governance.position_reconciler import (
    PositionReconciler,
)

from quant_ecosystem.execution.execution_audit import (
    log_execution_event,
)


class PositionTruthMonitor:

    def __init__(self):
        self._reconciler = (
            PositionReconciler()
        )

    def verify(
        self,
        broker_name,
        broker,
        internal_positions,
    ):

        result = (
            self._reconciler.reconcile(
                broker_name=broker_name,
                broker=broker,
                internal_positions=internal_positions,
            )
        )

        if not result["matched"]:

            log_execution_event(
                {
                    "event_type":
                    "POSITION_MISMATCH",

                    "broker":
                    broker_name,

                    "mismatches":
                    result["mismatches"],
                }
            )

        return result