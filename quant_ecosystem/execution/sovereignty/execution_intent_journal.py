import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


INTENT_LOG = Path("logs/execution_intents.jsonl")

INFLIGHT_EVENTS = {
    "CREATED",
    "SUBMITTING",
    "ACKNOWLEDGED",
    "RECONCILING",
    "UNCERTAIN",
}

TERMINAL_EVENTS = {
    "FILLED",
    "PARTIAL",
    "REJECTED",
}


class ExecutionIntentJournal:
    """
    Durable sovereign execution journal.

    Pack54 Drop3:
    duplicate governance enabled
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or INTENT_LOG
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def create_intent(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        asset_class: str,
        broker_name: str,
        meta: Optional[Dict] = None,
        fingerprint: str = "",
    ) -> str:
        intent_id = str(uuid.uuid4())

        self._append(
            {
                "intent_id": intent_id,
                "event": "CREATED",
                "fingerprint": fingerprint,
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price,
                "asset_class": asset_class,
                "broker_name": broker_name,
                "broker_order_id": "",
                "meta": meta or {},
            }
        )

        return intent_id

    def record_event(
        self,
        *,
        intent_id: str,
        event: str,
        broker_order_id: str = "",
        payload: Optional[Dict] = None,
    ) -> None:
        self._append(
            {
                "intent_id": intent_id,
                "event": str(event).upper(),
                "broker_order_id": broker_order_id,
                "payload": payload or {},
            }
        )

    def has_inflight_fingerprint(
        self,
        fingerprint: str,
    ) -> bool:
        state = self.latest_state_by_fingerprint(
            fingerprint
        )
        return state in INFLIGHT_EVENTS

    def has_terminal_fingerprint(
        self,
        fingerprint: str,
    ) -> bool:
        state = self.latest_state_by_fingerprint(
            fingerprint
        )
        return state in TERMINAL_EVENTS

    def latest_state_by_fingerprint(
        self,
        fingerprint: str,
    ) -> str:
        if not fingerprint:
            return ""

        events = self.load_events()

        intent_ids = set()

        for event in events:
            if event.get("fingerprint") == fingerprint:
                intent_ids.add(
                    event.get("intent_id")
                )

        if not intent_ids:
            return ""

        latest_state = ""

        for event in events:
            if event.get("intent_id") in intent_ids:
                latest_state = (
                    str(event.get("event", ""))
                    .upper()
                    .strip()
                )

        return latest_state

    def load_events(self):
        if not self._path.exists():
            return []

        rows = []

        with self._path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                line = line.strip()

                if not line:
                    continue

                try:
                    rows.append(
                        json.loads(line)
                    )
                except Exception:
                    continue

        return rows

    def _append(
        self,
        payload: Dict,
    ) -> None:
        enriched = {
            "timestamp": datetime.utcnow().isoformat(),
            **payload,
        }

        with self._path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(enriched) + "\n"
            )