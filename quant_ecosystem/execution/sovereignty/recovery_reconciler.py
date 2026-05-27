import json
from typing import Dict, List


RECOVERABLE_EVENTS = {
    "ACKNOWLEDGED",
    "RECONCILING",
    "UNCERTAIN",
}


class SovereignRecoveryReconciler:
    """
    Crash recovery reconciliation using broker truth.
    """

    def __init__(
        self,
        journal,
        order_reconciler,
    ):
        self._journal = journal
        self._order_reconciler = order_reconciler

    def recover(
        self,
        broker_registry: Dict,
    ) -> List[Dict]:
        recovered = []

        intents = self._recoverable_intents()

        for intent in intents:
            broker_name = (
                intent.get("broker_name", "")
            )
            broker_order_id = (
                intent.get("broker_order_id", "")
            )

            if not broker_name:
                continue

            if not broker_order_id:
                continue

            broker = broker_registry.get(
                broker_name
            )

            if broker is None:
                continue

            try:
                result = (
                    self._order_reconciler
                    .wait_for_final_state(
                        broker_name=broker_name,
                        broker=broker,
                        order_id=broker_order_id,
                    )
                )

                self._journal.record_event(
                    intent_id=intent["intent_id"],
                    event="RECOVERED",
                    broker_order_id=broker_order_id,
                    payload=result,
                )

                terminal = (
                    result.get("status", "")
                    .upper()
                    .strip()
                )

                if terminal:
                    self._journal.record_event(
                        intent_id=intent["intent_id"],
                        event=terminal,
                        broker_order_id=broker_order_id,
                        payload=result,
                    )

                recovered.append(result)

            except Exception as exc:
                self._journal.record_event(
                    intent_id=intent["intent_id"],
                    event="STILL_UNCERTAIN",
                    broker_order_id=broker_order_id,
                    payload={
                        "error": str(exc),
                    },
                )

        return recovered

    def _recoverable_intents(self):
        events = self._journal.load_events()

        latest = {}

        for event in events:
            intent_id = event.get("intent_id")

            if not intent_id:
                continue

            latest[intent_id] = event

        candidates = []

        for event in latest.values():
            status = (
                str(event.get("event", ""))
                .upper()
                .strip()
            )

            if status in RECOVERABLE_EVENTS:
                candidates.append(event)

        return candidates