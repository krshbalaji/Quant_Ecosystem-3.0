"""
signal_filter_engine.py
Multi-stage signal filter pipeline.
Stages (applied in order):
  1. RegimeFilter    — suppress signals misaligned with current market regime
  2. StrengthFilter  — drop signals below minimum strength
  3. CorrelationFilter — de-duplicate signals that are too correlated
  4. CooldownFilter  — enforce per-symbol cooldown periods
  5. ExposureFilter  — cap simultaneous open signals per asset class
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from quant_ecosystem.signal_factory.signal_generator_engine import RawSignal


# ---------------------------------------------------------------------------
# Individual Filters
# ---------------------------------------------------------------------------

class RegimeFilter:
    """
    Regime-aware signal suppression.
    Each strategy_type maps to regimes it is valid in.
    """

    # strategy rule type → accepted regimes
    _REGIME_MAP: Dict[str, Set[str]] = {
        "ema_cross":           {"TRENDING_BULL", "TRENDING_BEAR", "TREND", "LOW_VOLATILITY"},
        "trend_alignment":     {"TRENDING_BULL", "TRENDING_BEAR", "TREND"},
        "macd_histogram":      {"TRENDING_BULL", "TRENDING_BEAR", "TREND", "LOW_VOLATILITY"},
        "rsi_threshold":       {"RANGE_BOUND", "LOW_VOLATILITY", "MEAN_REVERSION"},
        "bb_reversion":        {"RANGE_BOUND", "LOW_VOLATILITY", "MEAN_REVERSION"},
        "stat_arb_zscore":     {"RANGE_BOUND", "LOW_VOLATILITY", "MEAN_REVERSION"},
        "volatility_breakout": {"HIGH_VOLATILITY", "CRASH_EVENT", "CRISIS"},
        "volume_confirmation": {"TRENDING_BULL", "TRENDING_BEAR", "RANGE_BOUND", "TREND"},
        "volume_spike":        {"HIGH_VOLATILITY", "TRENDING_BULL", "TRENDING_BEAR"},
    }

    def __init__(
        self,
        current_regime: str = "UNKNOWN",
        strategy_rule_map: Optional[Dict[str, str]] = None,
        strict: bool = False, **kwargs
    ) -> None:
        self.regime = str(current_regime).upper()
        self._strat_rule_map: Dict[str, str] = strategy_rule_map or {}
        self._strict = strict  # if True, filter ALL unknowns; if False, pass unknowns

    def update_regime(self, regime: str) -> None:
        self.regime = str(regime).upper()

    def passes(self, signal: RawSignal) -> bool:
        rule = self._strat_rule_map.get(signal.strategy_id, signal.metadata.get("rule_type", ""))
        allowed = self._REGIME_MAP.get(rule)
        if allowed is None:
            return not self._strict
        regime = signal.regime_hint.upper() if signal.regime_hint != "UNKNOWN" else self.regime
        return regime in allowed


class StrengthFilter:
    """Drop signals below a minimum strength threshold."""

    def __init__(self, min_strength: float = 0.15, **kwargs) -> None:
        self.min_strength = float(min_strength)

    def passes(self, signal: RawSignal) -> bool:
        return signal.strength >= self.min_strength


class CorrelationFilter:
    """
    Suppress duplicate signals on the same symbol within a time window.
    Handles the case where multiple strategies fire on the same symbol.
    """

    def __init__(self, window_seconds: float = 60.0, max_per_symbol: int = 3, **kwargs) -> None:
        self._window = float(window_seconds)
        self._max = int(max_per_symbol)
        self._history: Dict[str, List[float]] = defaultdict(list)

    def passes(self, signal: RawSignal) -> bool:
        now = time.time()
        key = f"{signal.symbol}|{signal.side}"
        # Evict old entries
        self._history[key] = [t for t in self._history[key] if now - t < self._window]
        if len(self._history[key]) >= self._max:
            return False
        self._history[key].append(now)
        return True

    def reset(self, symbol: Optional[str] = None) -> None:
        if symbol:
            for key in list(self._history.keys()):
                if key.startswith(symbol):
                    del self._history[key]
        else:
            self._history.clear()


class CooldownFilter:
    """Enforce per-(symbol, strategy) cooldown periods in seconds."""

    def __init__(self, cooldown_seconds: float = 300.0, **kwargs) -> None:
        self._cooldown = float(cooldown_seconds)
        self._last_signal: Dict[str, float] = {}

    def passes(self, signal: RawSignal) -> bool:
        key = f"{signal.strategy_id}|{signal.symbol}"
        now = time.time()
        last = self._last_signal.get(key, 0.0)
        if now - last < self._cooldown:
            return False
        self._last_signal[key] = now
        return True

    def reset(self, strategy_id: Optional[str] = None, symbol: Optional[str] = None) -> None:
        if strategy_id and symbol:
            self._last_signal.pop(f"{strategy_id}|{symbol}", None)
        elif strategy_id:
            for k in list(self._last_signal.keys()):
                if k.startswith(strategy_id):
                    del self._last_signal[k]
        else:
            self._last_signal.clear()


class ExposureFilter:
    """
    Cap simultaneous signals per asset class.
    Prevents over-concentration in one market.
    """

    # Infer asset class from symbol prefix
    _PREFIX_MAP: Dict[str, str] = {
        "NSE:": "stocks",
        "BSE:": "stocks",
        "MCX:": "commodities",
        "CRYPTO:": "crypto",
        "FX:": "forex",
        "NFO:": "futures",
        "BFO:": "futures",
        "CDS:": "forex",
    }

    def __init__(self, max_per_class: int = 4, **kwargs) -> None:
        self._max = int(max_per_class)
        self._current_counts: Dict[str, int] = defaultdict(int)
        self._session_symbols: Dict[str, Set[str]] = defaultdict(set)

    def passes(self, signal: RawSignal) -> bool:
        asset_class = self._classify(signal.symbol)
        if signal.symbol in self._session_symbols[asset_class]:
            return True  # already counting this symbol
        if self._current_counts[asset_class] >= self._max:
            return False
        self._current_counts[asset_class] += 1
        self._session_symbols[asset_class].add(signal.symbol)
        return True

    def _classify(self, symbol: str) -> str:
        for prefix, cls in self._PREFIX_MAP.items():
            if symbol.startswith(prefix):
                return cls
        return "unknown"

    def reset_session(self) -> None:
        self._current_counts.clear()
        self._session_symbols.clear()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class FilterResult:
    """Carries filtering output with rejection audit trail."""

    def __init__(self, **kwargs) -> None:
        self.passed: List[RawSignal] = []
        self.rejected: Dict[str, List[RawSignal]] = {
            "regime": [],
            "strength": [],
            "correlation": [],
            "cooldown": [],
            "exposure": [],
        }

    @property
    def pass_count(self) -> int:
        return len(self.passed)

    @property
    def reject_count(self) -> int:
        return sum(len(v) for v in self.rejected.values())

    def summary(self) -> Dict[str, Any]:
        return {
            "passed": self.pass_count,
            "rejected": {k: len(v) for k, v in self.rejected.items()},
            "total_in": self.pass_count + self.reject_count,
        }


class SignalFilterEngine:
    """
    Orchestrates all filter stages in sequence.

    Usage:
        engine = SignalFilterEngine(regime="TRENDING_BULL")
        result = engine.filter(raw_signals)
        clean_signals = result.passed
    """

    def __init__(
        self,
        regime: str = "UNKNOWN",
        min_strength: float = 0.15,
        cooldown_seconds: float = 300.0,
        correlation_window_seconds: float = 60.0,
        max_per_symbol: int = 3,
        max_per_asset_class: int = 4,
        strategy_rule_map: Optional[Dict[str, str]] = None,
        strict_regime: bool = False, **kwargs
    ) -> None:
        self._regime_filter = RegimeFilter(
            regime, strategy_rule_map=strategy_rule_map, strict=strict_regime
        )
        self._strength_filter = StrengthFilter(min_strength)
        self._correlation_filter = CorrelationFilter(correlation_window_seconds, max_per_symbol)
        self._cooldown_filter = CooldownFilter(cooldown_seconds)
        self._exposure_filter = ExposureFilter(max_per_asset_class)

    def update_regime(self, regime: str) -> None:
        self._regime_filter.update_regime(regime)

    def filter(self, signals: List[RawSignal]) -> FilterResult:
        result = FilterResult()
        for sig in signals:
            if not self._regime_filter.passes(sig):
                result.rejected["regime"].append(sig)
                continue
            if not self._strength_filter.passes(sig):
                result.rejected["strength"].append(sig)
                continue
            if not self._correlation_filter.passes(sig):
                result.rejected["correlation"].append(sig)
                continue
            if not self._cooldown_filter.passes(sig):
                result.rejected["cooldown"].append(sig)
                continue
            if not self._exposure_filter.passes(sig):
                result.rejected["exposure"].append(sig)
                continue
            result.passed.append(sig)
        return result

    def reset_session(self) -> None:
        self._correlation_filter.reset()
        self._exposure_filter.reset_session()

    def reset_cooldowns(self, strategy_id: Optional[str] = None) -> None:
        self._cooldown_filter.reset(strategy_id=strategy_id)

    def stats(self) -> Dict[str, Any]:
        return {
            "regime": self._regime_filter.regime,
            "min_strength": self._strength_filter.min_strength,
        }
