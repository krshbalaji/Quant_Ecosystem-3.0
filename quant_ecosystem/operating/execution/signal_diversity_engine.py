"""
signal_diversity_engine.py — Quant Ecosystem 3.0
================================================

Signal diversity and per-symbol cooldown management.

Responsibilities:
- Track per-symbol trading history to implement cooldown
- Ensure multi-signal type diversity (trend + mean reversion + breakout)
- Throttle max trades per cycle across all symbols  
- Detect over-trading single symbols
- Score signals by diversity contribution

Design:
- Non-invasive: works alongside ExecutionRouter
- Cooldown in cycles (e.g., 5 cycles min between trades on same symbol)
- Signal diversity metrics (what % of recent trades were each type)
- Integration with ExecutionRouter signal selection
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class PerSymbolCooldown:
    """Track cooldown state for individual symbols."""

    def __init__(self, cooldown_seconds: float = 60.0, max_trades_per_symbol_per_day: int = 5):
        """
        Parameters:
        -----------
        cooldown_seconds : float
            Minimum seconds between trades on same symbol
        max_trades_per_symbol_per_day : int
            Maximum trades per symbol per day
        """
        self.cooldown_seconds = cooldown_seconds
        self.max_trades_per_symbol_per_day = max_trades_per_symbol_per_day
        self.last_trade_time: Dict[str, float] = {}  # {symbol: timestamp}
        self.last_cycle_traded: Dict[str, int] = {}  # {symbol: cycle_num}
        self.trade_count_today: Dict[str, int] = defaultdict(int)
        self.last_reset_cycle = 0

    def can_trade(self, symbol: str, current_cycle: int) -> Tuple[bool, str]:
        """
        Check if symbol is available to trade.

        Returns:
        --------
        (allowed: bool, reason: str)
        """
        symbol = str(symbol).upper()
        now = time.time()
        
        # Check time-based cooldown
        if symbol in self.last_trade_time and now - self.last_trade_time[symbol] < self.cooldown_seconds:
            elapsed = now - self.last_trade_time[symbol]
            return False, f"COOLDOWN_ACTIVE_{elapsed:.1f}s_{self.cooldown_seconds}s"
        
        # Prevent duplicate trades in consecutive cycles
        if current_cycle == self.last_cycle_traded.get(symbol, -1):
            return False, "DUPLICATE_CONSECUTIVE_CYCLE"
        
        # Check max trades per symbol per day
        if self.trade_count_today.get(symbol, 0) >= self.max_trades_per_symbol_per_day:
            count = self.trade_count_today[symbol]
            return False, f"MAX_TRADES_PER_SYMBOL_{count}_{self.max_trades_per_symbol_per_day}"
        
        return True, "OK"

    def record_trade(self, symbol: str, cycle_num: int) -> None:
        """Record a trade on symbol."""
        symbol = str(symbol).upper()
        self.last_trade_time[symbol] = time.time()
        self.last_cycle_traded[symbol] = cycle_num
        self.trade_count_today[symbol] = self.trade_count_today.get(symbol, 0) + 1
        logger.info(
            "PerSymbolCooldown: Recorded trade on %s at cycle %d (count=%d)",
            symbol,
            cycle_num,
            self.trade_count_today[symbol],
        )

    def get_stats(self) -> Dict[str, any]:
        """Get current statistics."""
        return {
            "symbols_with_trades": len(self.last_trade_cycle),
            "total_trades_today": sum(self.trade_count_today.values()),
            "max_trades_per_symbol": max(self.trade_count_today.values()) if self.trade_count_today else 0,
            "avg_trades_per_symbol": (
                sum(self.trade_count_today.values()) / len(self.trade_count_today)
                if self.trade_count_today else 0
            ),
        }

    def reset_daily(self) -> None:
        """Reset daily counters (call at market open)."""
        self.last_trade_time.clear()
        self.last_cycle_traded.clear()
        self.trade_count_today.clear()
        logger.info("PerSymbolCooldown: Daily reset")


class SignalDiversityTracker:
    """Track signal type diversity to ensure multi-strategy balance."""

    def __init__(
        self,
        lookback_cycles: int = 50,
        min_diversity_score: float = 0.3,  # 30% from any single strategy type
    ):
        """
        Parameters:
        -----------
        lookback_cycles : int
            Window for diversity calculation
        min_diversity_score : float
            Min acceptable % for any single strategy type
        """
        self.lookback_cycles = lookback_cycles
        self.min_diversity_score = min_diversity_score
        self.signal_history: List[Dict] = []  # [{strategy_type, symbol, cycle, confidence}, ...]

    def record_signal(
        self,
        strategy_type: str,
        symbol: str,
        cycle_num: int,
        confidence: float,
    ) -> None:
        """Record a signal for diversity tracking."""
        self.signal_history.append({
            "strategy_type": str(strategy_type).upper(),
            "symbol": str(symbol).upper(),
            "cycle": cycle_num,
            "confidence": float(confidence),
        })
        
        # Prune old history
        if len(self.signal_history) > self.lookback_cycles:
            self.signal_history = self.signal_history[-self.lookback_cycles :]

    def get_diversity_score(self) -> Dict[str, float]:
        """
        Get diversity distribution across strategy types.

        Returns:
        --------
        {strategy_type: percent_of_total}
        """
        if not self.signal_history:
            return {"UNKNOWN": 1.0}
        
        type_counts = defaultdict(int)
        for sig in self.signal_history:
            type_counts[sig["strategy_type"]] += 1
        
        total = len(self.signal_history)
        return {stype: count / total for stype, count in type_counts.items()}

    def needs_diversity_boost(self, strategy_type: str) -> bool:
        """
        Check if this strategy type is over-represented.

        Returns:
        --------
        bool : True if we should avoid this strategy type right now
        """
        diversity = self.get_diversity_score()
        current_pct = diversity.get(str(strategy_type).upper(), 0.0)
        
        # If any strategy represents > 60% of recent signals, consider diversity boost
        return current_pct > 0.60

    def get_status(self) -> Dict[str, any]:
        """Get current status."""
        diversity = self.get_diversity_score()
        max_type = max(diversity.items(), key=lambda x: x[1])[0] if diversity else "NONE"
        max_pct = max(diversity.values()) if diversity else 0.0
        
        return {
            "diversity_by_type": diversity,
            "dominant_type": max_type,
            "dominant_pct": round(max_pct * 100.0, 1),
            "signal_count": len(self.signal_history),
        }


class MaxTradesPerCycleThrottle:
    """Enforce max trades per cycle limit."""

    def __init__(self, max_trades_per_cycle: int = 3):
        """
        Parameters:
        -----------
        max_trades_per_cycle : int
            Max number of trades allowed per single cycle
        """
        self.max_trades_per_cycle = max_trades_per_cycle
        self.cycle_trade_count: Dict[int, int] = {}

    def can_trade(self, current_cycle: int) -> Tuple[bool, str]:
        """
        Check if cycle trade quota is available.

        Returns:
        --------
        (allowed: bool, reason: str)
        """
        count = self.cycle_trade_count.get(current_cycle, 0)
        if count >= self.max_trades_per_cycle:
            return False, f"CYCLE_QUOTA_EXCEEDED_{count}_{self.max_trades_per_cycle}"
        return True, "OK"

    def record_trade(self, cycle_num: int) -> None:
        """Record a trade in current cycle."""
        self.cycle_trade_count[cycle_num] = self.cycle_trade_count.get(cycle_num, 0) + 1
        logger.info(
            "MaxTradesPerCycleThrottle: Cycle %d trade count = %d",
            cycle_num,
            self.cycle_trade_count[cycle_num],
        )


class SignalDiversityEngine:
    """
    Central coordinator for signal diversity and trading throttles.

    Combines:
    - PerSymbolCooldown: Avoid over-trading same symbol
    - SignalDiversityTracker: Balance across strategy types
    - MaxTradesPerCycleThrottle: Limit trades per cycle
    """

    def __init__(
        self,
        cooldown_seconds: float = 60.0,
        max_trades_per_cycle: int = 3,
        lookback_cycles: int = 50,
        max_trades_per_symbol_per_day: int = 5,
    ):
        self.cooldown = PerSymbolCooldown(cooldown_seconds=cooldown_seconds, max_trades_per_symbol_per_day=max_trades_per_symbol_per_day)
        self.diversity = SignalDiversityTracker(lookback_cycles=lookback_cycles)
        self.throttle = MaxTradesPerCycleThrottle(max_trades_per_cycle=max_trades_per_cycle)

    def should_execute_signal(
        self,
        symbol: str,
        strategy_type: str,
        cycle_num: int,
    ) -> Tuple[bool, str]:
        """
        Comprehensive check before executing signal.

        Returns:
        --------
        (should_execute: bool, reason: str)
        """
        # Check per-symbol cooldown
        can_trade_sym, reason_sym = self.cooldown.can_trade(symbol, cycle_num)
        if not can_trade_sym:
            return False, f"SYMBOL_COOLDOWN: {reason_sym}"
        
        # Check cycle throttle
        can_trade_cycle, reason_cycle = self.throttle.can_trade(cycle_num)
        if not can_trade_cycle:
            return False, f"CYCLE_THROTTLE: {reason_cycle}"
        
        # Check diversity (optional: penalize over-represented strategies)
        needs_diversity = self.diversity.needs_diversity_boost(strategy_type)
        if needs_diversity:
            logger.info(
                "SignalDiversityEngine: Strategy %s over-represented, penalizing",
                strategy_type,
            )
            # Could return reject here, but we'll just log for now
            # This makes diversity a soft constraint, not hard veto
        
        return True, "OK"

    def record_executed_signal(
        self,
        symbol: str,
        strategy_type: str,
        cycle_num: int,
        confidence: float,
    ) -> None:
        """Record signal that was actually executed."""
        self.cooldown.record_trade(symbol, cycle_num)
        self.diversity.record_signal(strategy_type, symbol, cycle_num, confidence)
        self.throttle.record_trade(cycle_num)

    def get_stats(self) -> Dict[str, any]:
        """Get comprehensive statistics."""
        return {
            "per_symbol_cooldown": self.cooldown.get_stats(),
            "signal_diversity": self.diversity.get_status(),
        }

    def reset_daily(self) -> None:
        """Reset daily counters at market open."""
        self.cooldown.reset_daily()
        logger.info("SignalDiversityEngine: Daily reset")


# Global singleton instance
_signal_diversity_engine: Optional[SignalDiversityEngine] = None


def get_signal_diversity_engine(
    cooldown_seconds: float = 60.0,
    max_trades_per_cycle: int = 3,
    max_trades_per_symbol_per_day: int = 5,
) -> SignalDiversityEngine:
    """Get or create the global signal diversity engine."""
    global _signal_diversity_engine
    if _signal_diversity_engine is None:
        _signal_diversity_engine = SignalDiversityEngine(
            cooldown_seconds=cooldown_seconds,
            max_trades_per_cycle=max_trades_per_cycle,
            max_trades_per_symbol_per_day=max_trades_per_symbol_per_day,
        )
    return _signal_diversity_engine
