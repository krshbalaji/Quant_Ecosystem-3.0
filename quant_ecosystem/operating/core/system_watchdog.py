from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class SystemWatchdog:
    """Tracks loop health and lightly restarts stale components when possible."""

    def __init__(
        self,
        freeze_timeout_sec: float = 20.0,
        latency_warn_ms: float = 1500.0,
        storage_path: str | Path = "storage/logs/watchdog.jsonl",
    ) -> None:
        self.freeze_timeout_sec = float(freeze_timeout_sec)
        self.latency_warn_ms = float(latency_warn_ms)
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._components: dict[str, dict[str, Any]] = {}

    def heartbeat(self, component: str, latency_ms: float = 0.0, cycle_id: int | None = None) -> None:
        now = time.time()
        self._components[str(component)] = {
            "last_seen_ts": now,
            "latency_ms": float(latency_ms or 0.0),
            "cycle_id": cycle_id,
        }
        if float(latency_ms or 0.0) >= self.latency_warn_ms:
            self._record("WARNING", component, f"High latency {round(float(latency_ms), 2)}ms", cycle_id=cycle_id)

    def evaluate(self) -> list[dict[str, Any]]:
        now = time.time()
        anomalies = []
        for component, payload in dict(self._components).items():
            age = now - float(payload.get("last_seen_ts", 0.0) or 0.0)
            if age > self.freeze_timeout_sec:
                event = {
                    "level": "ERROR",
                    "component": component,
                    "reason": "loop_freeze_detected",
                    "age_sec": round(age, 2),
                    "cycle_id": payload.get("cycle_id"),
                }
                anomalies.append(event)
                self._record("ERROR", component, f"Loop freeze detected after {round(age, 2)}s", cycle_id=payload.get("cycle_id"))
        return anomalies

    def restart_component(self, component: str, target: Any) -> str:
        for method_name in ("restart", "start", "reload"):
            method = getattr(target, method_name, None)
            if callable(method):
                method()
                self._record("INFO", component, f"Restarted using {method_name}()")
                return f"{component} restarted via {method_name}()"
        self._record("WARNING", component, "Restart requested but no restart hook was available")
        return f"{component} restart hook unavailable"

    def snapshot(self) -> dict[str, Any]:
        return dict(self._components)

    def _record(self, level: str, component: str, message: str, cycle_id: int | None = None) -> None:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level,
            "component": component,
            "cycle_id": cycle_id,
            "message": message,
        }
        try:
            with self.storage_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Watchdog log write failed | error=%s", exc)
