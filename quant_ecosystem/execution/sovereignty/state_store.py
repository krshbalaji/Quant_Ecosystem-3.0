import json
import sqlite3
import threading
import time

from pathlib import Path


DB_PATH = Path(
    "state/sovereign_state.db"
)


class SovereignStateStore:

    def __init__(
        self,
        db_path=None,
    ):
        self._db_path = Path(
            db_path or DB_PATH
        )

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

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_locks (
                    lock_key TEXT PRIMARY KEY,
                    owner TEXT,
                    expires_at INTEGER
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sovereign_state (
                    state_key TEXT PRIMARY KEY,
                    payload TEXT,
                    updated_at INTEGER
                )
                """
            )

            conn.commit()

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

                conn.commit()

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

    def acquire_lock(
        self,
        lock_key,
        owner,
        ttl_seconds=30,
    ):

        now = int(time.time())
        expiry = now + ttl_seconds

        with self._lock:

            self._init_db()

            with self._connect() as conn:

                row = conn.execute(
                    """
                    SELECT owner, expires_at
                    FROM execution_locks
                    WHERE lock_key = ?
                    """,
                    (lock_key,),
                ).fetchone()

                if row:

                    existing_expiry = row[1]

                    if existing_expiry > now:
                        return False

                    conn.execute(
                        """
                        UPDATE execution_locks
                        SET owner = ?, expires_at = ?
                        WHERE lock_key = ?
                        """,
                        (
                            owner,
                            expiry,
                            lock_key,
                        ),
                    )

                    conn.commit()

                    return True

                conn.execute(
                    """
                    INSERT INTO execution_locks (
                        lock_key,
                        owner,
                        expires_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        lock_key,
                        owner,
                        expiry,
                    ),
                )

                conn.commit()

                return True

    def release_lock(
        self,
        lock_key,
        owner,
    ):

        with self._lock:
            with self._connect() as conn:

                conn.execute(
                    """
                    DELETE FROM execution_locks
                    WHERE lock_key = ?
                    AND owner = ?
                    """,
                    (
                        lock_key,
                        owner,
                    ),
                )

                conn.commit()


sovereign_state_store = (
    SovereignStateStore()
)