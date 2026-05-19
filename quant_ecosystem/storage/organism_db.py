import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


DB_FILE = "qe3_organism.db"
DB_PATH = Path(os.getenv("QE3_ORGANISM_DB", Path(__file__).resolve().parents[2] / DB_FILE))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps_json(value: Any) -> str:
    return json.dumps(value or {}, separators=(",", ":"), sort_keys=True)


def loads_json(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                profile TEXT NOT NULL,
                strategy TEXT,
                confidence REAL,
                horizon TEXT,
                source TEXT,
                signal_timestamp TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty INTEGER NOT NULL,
                order_type TEXT,
                profile TEXT NOT NULL,
                reason TEXT,
                approval_id TEXT,
                source TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                qty INTEGER NOT NULL,
                avg_entry REAL NOT NULL,
                profile TEXT NOT NULL,
                strategy TEXT,
                thesis TEXT,
                lifecycle TEXT,
                pnl_realized REAL DEFAULT 0,
                pnl_unrealized REAL DEFAULT 0,
                source TEXT,
                metadata TEXT,
                UNIQUE(symbol, profile)
            );

            CREATE TABLE IF NOT EXISTS portfolio_decisions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                action TEXT NOT NULL,
                symbol TEXT,
                confidence REAL,
                reason TEXT,
                profile TEXT NOT NULL,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                symbol TEXT,
                side TEXT,
                profile TEXT,
                status TEXT,
                requested_by TEXT,
                approved_by TEXT,
                expires_at TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS risk_state (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                profile TEXT,
                status TEXT,
                risk_level TEXT,
                reason TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS capital_buckets (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                profile TEXT NOT NULL UNIQUE,
                allocated_capital REAL DEFAULT 0,
                used_capital REAL DEFAULT 0,
                available_capital REAL DEFAULT 0,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS telemetry_events (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                profile TEXT,
                symbol TEXT,
                severity TEXT,
                message TEXT,
                metadata TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
            CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_positions_symbol_profile ON positions(symbol, profile);
            CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON portfolio_decisions(created_at);
            """
        )


def row_to_dict(row: sqlite3.Row | None, json_fields: Iterable[str] = ()) -> Optional[Dict[str, Any]]:
    if row is None:
        return None

    data = dict(row)
    for field in json_fields:
        if field in data:
            data[field] = loads_json(data[field])
    return data
