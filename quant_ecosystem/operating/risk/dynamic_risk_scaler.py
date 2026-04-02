"""
dynamic_risk_scaler.py — Quant Ecosystem 3.0
=============================================

Dynamic risk scaling based on real-time performance metrics.

Responsibilities:
- Scale position size down based on current drawdown
- Detect abnormal activity patterns (loss streaks, declining win rate)
- Trigger global kill switch on severe anomalies
- Adjust risk budget dynamically based on equity curve shape

Design:
- Non-invasive: works alongside existing RiskEngine
- Feeds dynamic risk scaling factor to ExecutionRouter
- Tracks regime-specific risk profiles (avoid over-trading in losses)
- Integrates with ShutdownHandler for emergency stops
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DrawdownTracker:
    """Track peak-to-trough equity drawdown and scale risk accordingly."""

    def __init__(
        self,
        max_drawdown_pct: float = 15.0,
        critical_drawdown_pct: float = 25.0,
        peak_memory_cycles: int = 260,  # ~1 day of 5-min cycles
    ):
        """
        Parameters:
        -----------
        max_drawdown_pct : float
            Trigger first-stage risk reduction (50% of base risk)
        critical_drawdown_pct : float
            Trigger second-stage risk reduction (25% of base risk)
        peak_memory_cycles : int
            Number of cycles to keep peak equity history for rolling max
        """
        self.max_drawdown_pct = max_drawdown_pct
        self.critical_drawdown_pct = critical_drawdown_pct
        self.peak_memory_cycles = peak_memory_cycles

        self.peak_equity = 100_000.0
        self.current_equity = 100_000.0
        self.peak_history: List[Tuple[int, float]] = [(0, 100_000.0)]
        self.cycle_count = 0

        # Risk scaling state
        self.risk_scale_factor = 1.0  # Multiplied by base position size
        self.last_update_cycle = 0
        self.dd_stage = "NORMAL"  # NORMAL | ELEVATED | CRITICAL | LOCKED

    def update(self, current_equity: float, cycle_num: int = None) -> str:
        """
        Update equity and recalculate drawdown + risk scaling.

        Returns:
        --------
        str : Current drawdown stage (NORMAL, ELEVATED, CRITICAL, LOCKED)
        """
        if cycle_num is None:
            cycle_num = self.cycle_count
        self.cycle_count = max(self.cycle_count, cycle_num)
        self.current_equity = current_equity

        # Update peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.peak_history.append((cycle_num, current_equity))

        # Prune old peak history
        if len(self.peak_history) > self.peak_memory_cycles:
            self.peak_history = self.peak_history[-self.peak_memory_cycles :]

        # Calculate drawdown
        if self.peak_equity > 0:
            dd_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100.0
        else:
            dd_pct = 0.0

        # Determine stage and risk scaling
        if dd_pct >= self.critical_drawdown_pct:
            self.dd_stage = "CRITICAL"
            self.risk_scale_factor = 0.25  # 25% of normal risk
        elif dd_pct >= self.max_drawdown_pct:
            self.dd_stage = "ELEVATED"
            self.risk_scale_factor = 0.50  # 50% of normal risk
        else:
            self.dd_stage = "NORMAL"
            self.risk_scale_factor = 1.0  # Full risk

        self.last_update_cycle = cycle_num

        if cycle_num % 100 == 0:  # Log every 100 cycles
            logger.info(
                "DrawdownTracker: eq=%.2f peak=%.2f dd=%.2f%% stage=%s scale=%.2f",
                current_equity,
                self.peak_equity,
                dd_pct,
                self.dd_stage,
                self.risk_scale_factor,
            )

        return self.dd_stage

    def get_risk_scale_factor(self) -> float:
        """Get current risk scaling factor [0.25, 0.5, 1.0]."""
        return self.risk_scale_factor

    def get_stage(self) -> str:
        """Get current drawdown stage."""
        return self.dd_stage


class AbnormalActivityDetector:
    """Detect unusual trading patterns that suggest system malfunction or anomaly."""

    def __init__(
        self,
        max_consecutive_losses: int = 5,
        min_win_rate_pct: float = 35.0,
        loss_streak_window_cycles: int = 100,
        critical_loss_ratio: float = 0.80,  # 80% losses → anomaly
    ):
        """
        Parameters:
        -----------
        max_consecutive_losses : int
            Trigger warning if this many consecutive losing trades
        min_win_rate_pct : float
            Trigger warning if win_rate drops below this
        loss_streak_window_cycles : int
            Lookback window for calculating loss ratio
        critical_loss_ratio : float
            If losses/total > this ratio → critical anomaly
        """
        self.max_consecutive_losses = max_consecutive_losses
        self.min_win_rate_pct = min_win_rate_pct
        self.loss_streak_window_cycles = loss_streak_window_cycles
        self.critical_loss_ratio = critical_loss_ratio

        self.trade_history: List[Dict] = []  # [{"pnl": float, "cycle": int}, ...]
        self.is_anomaly = False
        self.anomaly_reason = ""
        self.consecutive_losses = 0
        self.total_trades_today = 0
        self.winning_trades_today = 0
        self.last_reset_ts = datetime.now()

    def reset_daily(self) -> None:
        """Reset daily counters (call at market open)."""
        self.consecutive_losses = 0
        self.total_trades_today = 0
        self.winning_trades_today = 0
        self.is_anomaly = False
        self.anomaly_reason = ""
        self.last_reset_ts = datetime.now()
        logger.info("AbnormalActivityDetector: Daily reset")

    def record_trade(self, pnl: float, cycle_num: int = 0) -> Tuple[bool, str]:
        """
        Record a trade result.

        Returns:
        --------
        (is_anomaly_triggered: bool, reason: str)
        """
        self.trade_history.append({"pnl": pnl, "cycle": cycle_num})
        self.total_trades_today += 1

        if pnl > 0:
            self.winning_trades_today += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.is_anomaly = True
            self.anomaly_reason = f"CONSECUTIVE_LOSSES_{self.consecutive_losses}"
            logger.warning(
                "🔴 ANOMALY: %d consecutive losses detected",
                self.consecutive_losses,
            )
            return True, self.anomaly_reason

        # Check win rate
        if self.total_trades_today >= 10:
            win_rate = (self.winning_trades_today / self.total_trades_today) * 100.0
            if win_rate < self.min_win_rate_pct:
                self.is_anomaly = True
                self.anomaly_reason = f"LOW_WIN_RATE_{win_rate:.1f}%"
                logger.warning(
                    "🔴 ANOMALY: Win rate %.1f%% below threshold %.1f%%",
                    win_rate,
                    self.min_win_rate_pct,
                )
                return True, self.anomaly_reason

        # Check loss ratio in window
        if len(self.trade_history) >= self.loss_streak_window_cycles:
            recent_trades = self.trade_history[-self.loss_streak_window_cycles :]
            loss_count = sum(1 for t in recent_trades if t["pnl"] <= 0)
            loss_ratio = loss_count / len(recent_trades)
            if loss_ratio >= self.critical_loss_ratio:
                self.is_anomaly = True
                self.anomaly_reason = f"CRITICAL_LOSS_RATIO_{loss_ratio:.2f}"
                logger.error(
                    "🔴 CRITICAL ANOMALY: Loss ratio %.2f%% in last %d trades",
                    loss_ratio * 100.0,
                    len(recent_trades),
                )
                return True, self.anomaly_reason

        self.is_anomaly = False
        self.anomaly_reason = "OK"
        return False, "OK"

    def is_anomalous(self) -> bool:
        """Check if current state is anomalous."""
        return self.is_anomaly

    def get_anomaly_reason(self) -> str:
        """Get reason for anomaly (or 'OK' if none)."""
        return self.anomaly_reason if self.is_anomaly else "OK"


class GlobalKillSwitch:
    """Emergency stop mechanism for severe anomalies or risk violations."""

    def __init__(self):
        self.is_triggered = False
        self.trigger_reason = ""
        self.trigger_time = None
        self.trigger_history: List[Tuple[datetime, str]] = []

    def trigger(self, reason: str) -> None:
        """Trigger the kill switch."""
        if self.is_triggered:
            return  # Already triggered

        self.is_triggered = True
        self.trigger_reason = reason
        self.trigger_time = datetime.now()
        self.trigger_history.append((self.trigger_time, reason))

        logger.critical(
            "🚨🚨🚨 GLOBAL KILL SWITCH TRIGGERED 🚨🚨🚨 Reason: %s", reason
        )

    def reset(self) -> None:
        """Reset kill switch (manual reset only, requires deliberate action)."""
        self.is_triggered = False
        self.trigger_reason = ""
        self.trigger_time = None
        logger.info("Global kill switch reset")

    def is_active(self) -> bool:
        """Check if kill switch is active."""
        return self.is_triggered

    def get_status(self) -> Dict[str, any]:
        """Get current status."""
        return {
            "is_triggered": self.is_triggered,
            "reason": self.trigger_reason,
            "triggered_at": self.trigger_time.isoformat() if self.trigger_time else None,
            "trigger_count": len(self.trigger_history),
        }


class DynamicRiskScaler:
    """
    Central coordinator for dynamic risk scaling.

    Combines:
    - DrawdownTracker: Scale down risk as equity drops
    - AbnormalActivityDetector: Flag unusual patterns
    - GlobalKillSwitch: Emergency stop on critical issues
    """

    def __init__(
        self,
        config=None,
        max_drawdown_pct: float = 15.0,
        critical_drawdown_pct: float = 25.0,
        max_consecutive_losses: int = 5,
    ):
        self.config = config
        self.drawdown_tracker = DrawdownTracker(
            max_drawdown_pct=max_drawdown_pct,
            critical_drawdown_pct=critical_drawdown_pct,
        )
        self.activity_detector = AbnormalActivityDetector(
            max_consecutive_losses=max_consecutive_losses
        )
        self.kill_switch = GlobalKillSwitch()

    def update_cycle(self, equity: float, cycle_num: int = 0) -> Dict[str, any]:
        """Process one cycle (called from main loop or orchestrator)."""
        dd_stage = self.drawdown_tracker.update(equity, cycle_num)
        risk_scale = self.drawdown_tracker.get_risk_scale_factor()

        status = {
            "cycle": cycle_num,
            "equity": equity,
            "dd_stage": dd_stage,
            "risk_scale": risk_scale,
            "kill_switch": self.kill_switch.is_active(),
            "anomaly": self.activity_detector.is_anomalous(),
            "anomaly_reason": self.activity_detector.get_anomaly_reason(),
        }

        return status

    def record_trade_result(self, pnl: float, cycle_num: int = 0) -> None:
        """Record a trade PnL and check for anomalies."""
        is_anomaly, reason = self.activity_detector.record_trade(pnl, cycle_num)
        if is_anomaly:
            self.kill_switch.trigger(f"TRADE_ANOMALY: {reason}")

    def reset_daily(self) -> None:
        """Reset daily counters at market open."""
        self.activity_detector.reset_daily()

    def get_risk_scale_factor(self) -> float:
        """Get current risk scaling factor [0.25, 0.5, 1.0]."""
        if self.kill_switch.is_active():
            return 0.0  # No trading
        return self.drawdown_tracker.get_risk_scale_factor()

    def get_status(self) -> Dict[str, any]:
        """Get comprehensive status."""
        return {
            "drawdown_stage": self.drawdown_tracker.get_stage(),
            "risk_scale_factor": self.drawdown_tracker.get_risk_scale_factor(),
            "consecutive_losses": self.activity_detector.consecutive_losses,
            "win_rate": (
                (self.activity_detector.winning_trades_today / self.activity_detector.total_trades_today * 100.0)
                if self.activity_detector.total_trades_today > 0
                else 0.0
            ),
            "kill_switch": self.kill_switch.get_status(),
        }


# Global singleton instance
_dynamic_risk_scaler: Optional[DynamicRiskScaler] = None


def get_dynamic_risk_scaler(config=None) -> DynamicRiskScaler:
    """Get or create the global dynamic risk scaler."""
    global _dynamic_risk_scaler
    if _dynamic_risk_scaler is None:
        _dynamic_risk_scaler = DynamicRiskScaler(config=config)
    return _dynamic_risk_scaler
