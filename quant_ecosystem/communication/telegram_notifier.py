from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertLevel(IntEnum):
    INFO = 10
    SUCCESS = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class Notification:
    alert_level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    icon: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def format(self) -> str:
        prefix = self.icon or self._icon()
        return f"{prefix} {self.title}\n{self.message}"

    def _icon(self) -> str:
        icons = {
            AlertLevel.INFO: "[i]",
            AlertLevel.SUCCESS: "[ok]",
            AlertLevel.WARNING: "[!]",
            AlertLevel.ERROR: "[x]",
            AlertLevel.CRITICAL: "[!!]",
        }
        return icons.get(self.alert_level, "[*]")


class TelegramNotifier:
    def __init__(
        self,
        send_callback: Callable[[str], Any],
        min_alert_level: AlertLevel = AlertLevel.INFO,
        batch_size: int = 1,
        batch_timeout: float = 2.0,
    ) -> None:
        self.send_callback = send_callback
        self.min_alert_level = min_alert_level
        self.batch_size = max(1, int(batch_size))
        self.batch_timeout = max(0.1, float(batch_timeout))
        self._queue: "queue.Queue[Notification]" = queue.Queue()
        self._running = False
        self._worker: Optional[threading.Thread] = None
        logger.info("[telegram] notifier initialized")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._worker_loop, name="TelegramNotifier", daemon=True)
        self._worker.start()
        logger.info("[telegram] notifier started")

    def stop(self, timeout: float = 5.0) -> None:
        self._running = False
        if self._worker is not None:
            self._worker.join(timeout=timeout)
        logger.info("[telegram] notifier stopped")

    def notify_strategy_discovered(self, strategy_id: str, fitness: float, indicator: Optional[str] = None) -> None:
        details = [f"ID: {strategy_id}", f"Fitness: {fitness:.4f}"]
        if indicator:
            details.append(f"Indicator: {indicator}")
        self._enqueue(
            Notification(
                alert_level=AlertLevel.SUCCESS,
                title="Strategy Discovered",
                message="\n".join(details),
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"strategy_id": strategy_id, "fitness": fitness},
            )
        )

    def notify_portfolio_event(
        self,
        event_type: str,
        symbol: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None,
    ) -> None:
        lines = [f"Event: {event_type}", f"Symbol: {symbol}", f"Qty: {quantity}", f"Price: {price:,.2f}"]
        if pnl is not None:
            lines.append(f"P&L: {pnl:,.2f}")
        self._enqueue(
            Notification(
                alert_level=AlertLevel.INFO,
                title="Portfolio Event",
                message="\n".join(lines),
                timestamp=datetime.now(tz=timezone.utc),
            )
        )

    def notify_risk_alert(self, alert_type: str, severity: str, message: str) -> None:
        level = AlertLevel.CRITICAL if severity.lower() == "high" else AlertLevel.WARNING
        self._enqueue(
            Notification(
                alert_level=level,
                title=f"Risk Alert: {alert_type}",
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
            )
        )

    def notify_milestone(self, milestone: str, details: Optional[str] = None) -> None:
        self._enqueue(
            Notification(
                alert_level=AlertLevel.SUCCESS,
                title=f"Milestone: {milestone}",
                message=details or "Milestone reached",
                timestamp=datetime.now(tz=timezone.utc),
            )
        )

    def notify_system_health(self, status: str, message: str, issues: Optional[List[str]] = None) -> None:
        lines = [message]
        for issue in issues or []:
            lines.append(f"- {issue}")
        level = AlertLevel.INFO if status == "healthy" else AlertLevel.WARNING
        self._enqueue(
            Notification(
                alert_level=level,
                title=f"System Health: {status}",
                message="\n".join(lines),
                timestamp=datetime.now(tz=timezone.utc),
            )
        )

    def notify_performance_update(
        self,
        metric_name: str,
        current_value: float,
        previous_value: Optional[float] = None,
        unit: str = "",
    ) -> None:
        message = f"{metric_name}: {current_value:.4f}{unit}"
        if previous_value is not None:
            message += f" (prev {previous_value:.4f}{unit})"
        self._enqueue(
            Notification(
                alert_level=AlertLevel.INFO,
                title="Performance Update",
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
            )
        )

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def _enqueue(self, notification: Notification) -> None:
        if notification.alert_level < self.min_alert_level:
            return
        self._queue.put(notification)

    def _worker_loop(self) -> None:
        while self._running:
            batch: List[Notification] = []
            try:
                first = self._queue.get(timeout=0.5)
                batch.append(first)
            except queue.Empty:
                continue

            deadline = datetime.now(tz=timezone.utc).timestamp() + self.batch_timeout
            while len(batch) < self.batch_size and datetime.now(tz=timezone.utc).timestamp() < deadline:
                try:
                    batch.append(self._queue.get(timeout=0.1))
                except queue.Empty:
                    break

            try:
                self.send_callback("\n\n".join(note.format() for note in batch))
            except Exception as exc:
                logger.warning("[telegram] notifier send failed: %s", exc)
