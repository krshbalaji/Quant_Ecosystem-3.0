import json
import sqlite3
import threading
from pathlib import Path


DB_PATH = Path("state/qe3_sovereign.db")


class SovereignStateStore:
    """
    Institutional durable state engine.
    SQLite transactional sovereignty layer.
    """

    def __init__(self, db_path=None):
        self._db_path = Path(db_path or DB_PATH)
        self._db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(
            str(self._db_path)
        )

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT,
                    event TEXT,
                    fingerprint TEXT,
                    broker_name TEXT,
                    broker_order_id TEXT,
                    payload TEXT,
                    ts DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def append_event(
        self,
        intent_id,
        event,
        fingerprint="",
        broker_name="",
        broker_order_id="",
        payload=None,
    ):
        payload = payload or {}

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO execution_events (
                        intent_id,
                        event,
                        fingerprint,
                        broker_name,
                        broker_order_id,
                        payload
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent_id,
                        event,
                        fingerprint,
                        broker_name,
                        broker_order_id,
                        json.dumps(payload),
                    ),
                )

    def load_events(self):
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        intent_id,
                        event,
                        fingerprint,
                        broker_name,
                        broker_order_id,
                        payload,
                        ts
                    FROM execution_events
                    ORDER BY id ASC
                    """
                ).fetchall()

        results = []

        for row in rows:
            results.append(
                {
                    "intent_id": row[0],
                    "event": row[1],
                    "fingerprint": row[2],
                    "broker_name": row[3],
                    "broker_order_id": row[4],
                    "payload": json.loads(
                        row[5] or "{}"
                    ),
                    "timestamp": row[6],
                }
            )

        return results


sovereign_state_store = SovereignStateStore()