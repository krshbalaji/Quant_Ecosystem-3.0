from typing import Any, Dict, List
from uuid import uuid4

from quant_ecosystem.contracts.order_intent import OrderIntent
from quant_ecosystem.storage.organism_db import dumps_json, get_connection, init_db, row_to_dict, utc_now


def record_order(order_intent: OrderIntent | Dict[str, Any]) -> str:
    init_db()
    if isinstance(order_intent, OrderIntent):
        data = order_intent.to_dict()
    else:
        data = OrderIntent.from_mapping(order_intent).to_dict()
    row_id = str(uuid4())
    now = utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO orders (
                id, created_at, updated_at, symbol, side, qty, order_type,
                profile, reason, approval_id, source, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                data["symbol"],
                data["side"],
                data["qty"],
                data["order_type"],
                data["profile"],
                data["reason"],
                data["approval_id"],
                data["source"],
                dumps_json(data["metadata"]),
            ),
        )
    return row_id


def get_recent_orders(limit: int = 100) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    results: List[Dict[str, Any]] = []

    for row in rows:
        item = row_to_dict(
            row,
            json_fields=("metadata",),
        )
        if item is not None:
            results.append(item)

    return results