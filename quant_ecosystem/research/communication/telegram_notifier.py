"""
telegram_notifier.py — Quant Ecosystem 3.0
===========================================

Event notification system for Telegram.

Sends real-time alerts for:
- Strategy discoveries
- Portfolio events (entries, exits)
- Risk alerts (drawdown, margin)
- Research milestones
- System health issues
- Performance updates

Thread-safe with queue-based delivery.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    
    INFO = "info"          # Informational
    SUCCESS = "success"    # Positive event
    WARNING = "warning"    # Warning
    ERROR = "error"        # Error
    CRITICAL = "critical"  # System-critical


@dataclass
class Notification:
    """Telegram notification."""
    
    alert_level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    icon: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def format(self) -> str:
        """Format for Telegram."""
        icon = self.icon or self._get_icon()
        return f"{icon} **{self.title}**\n{self.message}"
    
    def _get_icon(self) -> str:
        """Get icon for alert level."""
        icons = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.SUCCESS: "✅",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }
        return icons.get(self.alert_level, "•")


class TelegramNotifier:
    """
    Send notifications to Telegram.
    
    Features:
    - Queue-based async delivery
    - Rate limiting
    - Notification deduplication
    - Alert level filtering
    - Batch processing
    
    Parameters
    ----------
    send_callback : Callable
        Async callback to send message (receives message str)
    min_alert_level : AlertLevel, default=AlertLevel.INFO
        Minimum level to send (filters lower priority)
    batch_size : int, default=1
        Number of notifications per message
    batch_timeout : float, default=2.0
        Seconds to wait for batch before sending
    
    Examples
    --------
    >>> notifier = TelegramNotifier(send_callback=send_telegram_msg)
    >>> 
    >>> notifier.notify_strategy_discovered(
    ...     strategy_id="strat_001",
    ...     fitness=0.85
    ... )
    >>> 
    >>> notifier.notify_portfolio_event(
    ...     event_type="entry",
    ...     symbol="NSE:INFY",
    ...     price=1850.50
    ... )
    """
    
    def __init__(
        self,
        send_callback: Callable[[str], Any],
        min_alert_level: AlertLevel = AlertLevel.INFO,
        batch_size: int = 1,
        batch_timeout: float = 2.0,
    ) -> None:
        self.send_callback = send_callback
        self.min_alert_level = min_alert_level
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        self._queue: queue.Queue[Notification] = queue.Queue()
        self._dedup_cache: Dict[str, datetime] = {}
        self._dedup_ttl_seconds = 300  # 5 minutes
        self._lock = threading.RLock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        logger.info(
            "TelegramNotifier initialized "
            "(min_level=%s, batch_size=%d)",
            min_alert_level.value, batch_size
        )
    
    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    
    def start(self) -> None:
        """Start notification worker thread."""
        try:
            with self._lock:
                if self._running:
                    return
                
                self._running = True
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True
                )
                self._worker_thread.start()
                logger.info("TelegramNotifier started")
        
        except Exception as exc:
            logger.error("Failed to start notifier: %s", exc)
    
    def stop(self, timeout: float = 5.0) -> None:
        """Stop notification worker thread."""
        try:
            with self._lock:
                self._running = False
            
            if self._worker_thread:
                self._worker_thread.join(timeout=timeout)
                logger.info("TelegramNotifier stopped")
        
        except Exception as exc:
            logger.error("Failed to stop notifier: %s", exc)
    
    # -----------------------------------------------------------------------
    # Notification Methods
    # -----------------------------------------------------------------------
    
    def notify_strategy_discovered(
        self,
        strategy_id: str,
        fitness: float,
        indicator: Optional[str] = None,
    ) -> None:
        """Notify of strategy discovery."""
        try:
            message = f"New strategy discovered!\n"
            message += f"ID: `{strategy_id}`\n"
            message += f"Fitness: {fitness:.4f}"
            
            if indicator:
                message += f"\nIndicator: {indicator}"
            
            notification = Notification(
                alert_level=AlertLevel.SUCCESS,
                title="Strategy Discovered",
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"strategy_id": strategy_id, "fitness": fitness},
            )
            
            self._enqueue_notification(notification)
        
        except Exception as exc:
            logger.error("Failed to notify discovery: %s", exc)
    
    def notify_portfolio_event(
        self,
        event_type: str,  # "entry", "exit", "adjustment"
        symbol: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None,
    ) -> None:
        """Notify portfolio event."""
        try:
            icons = {
                "entry": "📈 Position Entry",
                "exit": "📉 Position Exit",
                "adjustment": "🔄 Position Adjusted",
            }
            
            title = icons.get(event_type, "Portfolio Event")
            
            message = f"Symbol: {symbol}\n"
            message += f"Qty: {quantity}\n"
            message += f"Price: ${price:,.2f}"
            
            if pnl is not None:
                message += f"\nP&L: ${pnl:,.2f}"
            
            notification = Notification(
                alert_level=AlertLevel.INFO,
                title=title,
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"symbol": symbol, "event": event_type},
            )
            
            self._enqueue_notification(notification)
        
        except Exception as exc:
            logger.error("Failed to notify portfolio event: %s", exc)
    
    def notify_risk_alert(
        self,
        alert_type: str,  # "drawdown", "margin", "volatility", "concentration"
        severity: str,    # "low", "medium", "high"
        message: str,
    ) -> None:
        """Notify risk alert."""
        try:
            level_map = {
                "low": AlertLevel.WARNING,
                "medium": AlertLevel.WARNING,
                "high": AlertLevel.CRITICAL,
            }
            
            title_map = {
                "drawdown": "Drawdown Alert",
                "margin": "Margin Alert",
                "volatility": "Volatility Alert",
                "concentration": "Concentration Alert",
            }
            
            notification = Notification(
                alert_level=level_map.get(severity, AlertLevel.WARNING),
                title=title_map.get(alert_type, "Risk Alert"),
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"type": alert_type, "severity": severity},
            )
            
            self._enqueue_notification(notification)
        
        except Exception as exc:
            logger.error("Failed to notify risk alert: %s", exc)
    
    def notify_milestone(
        self,
        milestone: str,  # "1000_strategies", "sharpe_2_0", "research_cycles_100"
        details: Optional[str] = None,
    ) -> None:
        """Notify research milestone."""
        try:
            milestone_names = {
                "1000_strategies": "🎉 1,000 Strategies!",
                "sharpe_2_0": "🏆 Sharpe Ratio ≥ 2.0!",
                "research_cycles_100": "📊 100 Research Cycles!",
                "new_best_sharpe": "🌟 New Best Sharpe!",
                "portfolio_million": "💰 $1M Portfolio!",
            }
            
            title = milestone_names.get(milestone, f"Milestone: {milestone}")
            
            message = "Congratulations! An important milestone has been reached."
            if details:
                message += f"\n\n{details}"
            
            notification = Notification(
                alert_level=AlertLevel.SUCCESS,
                title=title,
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"milestone": milestone},
            )
            
            self._enqueue_notification(notification)
        
        except Exception as exc:
            logger.error("Failed to notify milestone: %s", exc)
    
    def notify_system_health(
        self,
        status: str,  # "healthy", "degraded", "critical"
        message: str,
        issues: Optional[List[str]] = None,
    ) -> None:
        """Notify system health status."""
        try:
            level_map = {
                "healthy": AlertLevel.INFO,
                "degraded": AlertLevel.WARNING,
                "critical": AlertLevel.CRITICAL,
            }
            
            title_map = {
                "healthy": "✅ System Healthy",
                "degraded": "⚠️ System Degraded",
                "critical": "🚨 Critical Issue",
            }
            
            full_message = message
            if issues:
                full_message += "\n\nIssues:\n"
                for issue in issues[:5]:
                    full_message += f"• {issue}\n"
                if len(issues) > 5:
                    full_message += f"• ... +{len(issues) - 5} more"
            
            notification = Notification(
                alert_level=level_map.get(status, AlertLevel.WARNING),
                title=title_map.get(status, "System Status"),
                message=full_message,
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"status": status},
            )
            
            self._enqueue_notification(notification)
        
        except Exception as exc:
            logger.error("Failed to notify system health: %s", exc)
    
    def notify_performance_update(
        self,
        metric_name: str,
        current_value: float,
        previous_value: Optional[float] = None,
        unit: str = "",
    ) -> None:
        """Notify performance metric update."""
        try:
            # Determine change
            change_str = ""
            if previous_value is not None:
                change = current_value - previous_value
                change_pct = (change / abs(previous_value) * 100) if previous_value != 0 else 0
                change_str = f" ({change:+.2f} / {change_pct:+.1f}%)"
            
            message = f"{metric_name}: {current_value:.4f}{unit}{change_str}"
            
            notification = Notification(
                alert_level=AlertLevel.INFO,
                title="Performance Update",
                message=message,
                timestamp=datetime.now(tz=timezone.utc),
                metadata={"metric": metric_name, "value": current_value},
            )
            
            self._enqueue_notification(notification)
        
        except Exception as exc:
            logger.error("Failed to notify performance update: %s", exc)
    
    # -----------------------------------------------------------------------
    # Private Methods
    # -----------------------------------------------------------------------
    
    def _enqueue_notification(self, notification: Notification) -> None:
        """Enqueue notification if it passes filters."""
        try:
            # Check alert level
            if notification.alert_level.value < self.min_alert_level.value:
                return
            
            # Check deduplication
            dedup_key = f"{notification.title}_{notification.alert_level.value}"
            
            with self._lock:
                if dedup_key in self._dedup_cache:
                    last_time = self._dedup_cache[dedup_key]
                    age = (datetime.now(tz=timezone.utc) - last_time).total_seconds()
                    
                    if age < self._dedup_ttl_seconds:
                        logger.debug("Notification deduplicated: %s", notification.title)
                        return
                
                self._dedup_cache[dedup_key] = datetime.now(tz=timezone.utc)
            
            # Enqueue
            self._queue.put(notification)
        
        except Exception as exc:
            logger.error("Failed to enqueue notification: %s", exc)
    
    def _worker_loop(self) -> None:
        """Worker thread main loop."""
        try:
            batch = []
            last_send = datetime.now(tz=timezone.utc)
            
            while self._running:
                try:
                    # Try to get notification with timeout
                    try:
                        notification = self._queue.get(timeout=0.5)
                        batch.append(notification)
                    except queue.Empty:
                        pass
                    
                    # Check if should send
                    should_send = False
                    
                    if len(batch) >= self.batch_size:
                        should_send = True
                    elif batch:
                        age = (datetime.now(tz=timezone.utc) - last_send).total_seconds()
                        if age >= self.batch_timeout:
                            should_send = True
                    
                    # Send batch
                    if should_send and batch:
                        self._send_batch(batch)
                        batch = []
                        last_send = datetime.now(tz=timezone.utc)
                
                except Exception as exc:
                    logger.error("Worker loop error: %s", exc)
        
        except Exception as exc:
            logger.error("Worker thread crashed: %s", exc)
        finally:
            logger.info("Notifier worker thread stopped")
    
    def _send_batch(self, notifications: List[Notification]) -> None:
        """Send batch of notifications."""
        try:
            # Format messages
            messages = [n.format() for n in notifications]
            combined = "\n\n".join(messages)
            
            # Send via callback
            try:
                result = self.send_callback(combined)
                
                # Handle async callback
                if asyncio.iscoroutine(result):
                    asyncio.run(result)
                
                logger.debug("Sent batch of %d notifications", len(notifications))
            
            except Exception as exc:
                logger.error("Failed to send notifications: %s", exc)
        
        except Exception as exc:
            logger.error("Batch send error: %s", exc)
    
    def get_queue_size(self) -> int:
        """Get pending notifications count."""
        return self._queue.qsize()
