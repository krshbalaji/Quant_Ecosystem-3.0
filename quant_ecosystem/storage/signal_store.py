from typing import Any, Dict, List
from uuid import uuid4

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.storage.organism_db import dumps_json, get_connection, init_db, row_to_dict, utc_now


def record_signal(signal_intent: SignalIntent | Dict[str, Any]) -> str:
    init_db()
    data = signal_intent.to_dict() if hasattr(signal_intent, "to_dict") else SignalIntent.from_mapping(signal_intent).to_dict()
    row_id = str(uuid4())
    now = utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO signals (
                id, created_at, updated_at, symbol, side, profile, strategy,
                confidence, horizon, source, signal_timestamp, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                data["symbol"],
                data["side"],
                data["profile"],
                data["strategy"],
                data["confidence"],
                data["horizon"],
                data["source"],
                data["timestamp"],
                dumps_json(data["metadata"]),
            ),
        )
    return row_id


def get_recent_signals(limit: int = 100) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [row_to_dict(row, json_fields=("metadata",)) for row in rows]
