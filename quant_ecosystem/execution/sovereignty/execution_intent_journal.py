import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


INTENT_LOG = Path("logs/execution_intents.jsonl")


class ExecutionIntentJournal:
    """
    Durable append-only sovereign execution intent journal.

    Pack54 Drop1:
    infrastructure only
    no enforcement logic yet
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
                "event": event,
                "broker_order_id": broker_order_id,
                "payload": payload or {},
            }
        )

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