from typing import Any, Dict, List, Optional
from uuid import uuid4

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.signal_intent import _profile_value
from quant_ecosystem.storage.organism_db import dumps_json, get_connection, init_db as _init_db, row_to_dict, utc_now


def init_db() -> None:
    _init_db()


def get_all_positions() -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM positions ORDER BY updated_at DESC"
        ).fetchall()
    results: List[Dict[str, Any]] = []

    for row in rows:
        item = row_to_dict(
            row,
            json_fields=("thesis", "metadata"),
        )
        if item is not None:
            results.append(item)

    return results


def get_position(symbol: str, profile: Optional[str] = None) -> Optional[Dict[str, Any]]:
    init_db()
    query = "SELECT * FROM positions WHERE symbol = ?"
    params: list[Any] = [symbol]

    if profile:
        query += " AND profile = ?"
        params.append(_profile_value(profile))

    query += " ORDER BY updated_at DESC LIMIT 1"

    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
    return row_to_dict(row, json_fields=("thesis", "metadata"))


def upsert_position(position: Position | Dict[str, Any]) -> str:
    init_db()
    if isinstance(position, Position):
        data = position.to_dict()
    else:
        data = Position.from_mapping(position).to_dict()
    now = utc_now()
    existing = get_position(data["symbol"], data["profile"])
    row_id = existing["id"] if existing else str(uuid4())
    created_at = existing["created_at"] if existing else now

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO positions (
                id, created_at, updated_at, symbol, qty, avg_entry, profile,
                strategy, thesis, lifecycle, pnl_realized, pnl_unrealized,
                source, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, profile) DO UPDATE SET
                updated_at=excluded.updated_at,
                qty=excluded.qty,
                avg_entry=excluded.avg_entry,
                strategy=excluded.strategy,
                thesis=excluded.thesis,
                lifecycle=excluded.lifecycle,
                pnl_realized=excluded.pnl_realized,
                pnl_unrealized=excluded.pnl_unrealized,
                source=excluded.source,
                metadata=excluded.metadata
            """,
            (
                row_id,
                created_at,
                now,
                data["symbol"],
                data["qty"],
                data["avg_entry"],
                data["profile"],
                data["strategy"],
                dumps_json(data["thesis"]),
                data["lifecycle"],
                data["pnl_realized"],
                data["pnl_unrealized"],
                data["source"],
                dumps_json(data["metadata"]),
            ),
        )
    return row_id


def close_position(symbol: str, profile: Optional[str] = None) -> int:
    init_db()
    now = utc_now()
    query = "UPDATE positions SET lifecycle = ?, qty = ?, updated_at = ? WHERE symbol = ?"
    params: list[Any] = ["CLOSED", 0, now, symbol]

    if profile:
        query += " AND profile = ?"
        params.append(_profile_value(profile))

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.rowcount


def delete_position(symbol: str, profile: Optional[str] = None) -> int:
    init_db()
    query = "DELETE FROM positions WHERE symbol = ?"
    params: list[Any] = [symbol]

    if profile:
        query += " AND profile = ?"
        params.append(_profile_value(profile))

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.rowcount
