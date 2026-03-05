"""
signal_generator_engine.py
Converts feature snapshots into raw directional signals for each strategy.
Each strategy has a SignalRule that maps features → (side, strength, metadata).
This module is the bridge between feature_lab outputs and execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from quant_ecosystem.feature_lab.feature_store import FeatureStore


# ---------------------------------------------------------------------------
# Signal data structures
# ---------------------------------------------------------------------------

@dataclass
class RawSignal:
    """Unfiltered signal from a single strategy on a single symbol."""
    strategy_id: str
    symbol: str
    side: str                   # BUY | SELL | HOLD
    strength: float             # [0, 1] raw confidence
    features_used: List[str]    # which features drove the decision
    timestamp: float = field(default_factory=time.time)
    regime_hint: str = "UNKNOWN"
    timeframe: str = "5m"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "strength": round(self.strength, 6),
            "features_used": self.features_used,
            "timestamp": self.timestamp,
            "regime_hint": self.regime_hint,
            "timeframe": self.timeframe,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Built-in signal rules (vectorized)
# ---------------------------------------------------------------------------

def _rule_ema_cross(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """EMA crossover — ema_9 vs ema_21."""
    e9 = features.get("ema_9", 0.0)
    e21 = features.get("ema_21", 0.0)
    slope = features.get("ema_9_slope_pct", 0.0)
    if e9 == 0 or e21 == 0:
        return None
    if e9 > e21 and slope > 0:
        strength = min(1.0, abs(e9 - e21) / e21 * 100)
        return RawSignal("", "", "BUY", strength, ["ema_9", "ema_21", "ema_9_slope_pct"])
    if e9 < e21 and slope < 0:
        strength = min(1.0, abs(e21 - e9) / e21 * 100)
        return RawSignal("", "", "SELL", strength, ["ema_9", "ema_21", "ema_9_slope_pct"])
    return None


def _rule_rsi_threshold(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """RSI oversold/overbought."""
    rsi = features.get("rsi_14", 50.0)
    oversold = float(params.get("oversold", 30.0))
    overbought = float(params.get("overbought", 70.0))
    if rsi < oversold:
        strength = (oversold - rsi) / oversold
        return RawSignal("", "", "BUY", min(1.0, strength), ["rsi_14"])
    if rsi > overbought:
        strength = (rsi - overbought) / (100 - overbought)
        return RawSignal("", "", "SELL", min(1.0, strength), ["rsi_14"])
    return None


def _rule_macd_histogram(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """MACD histogram momentum."""
    hist = features.get("macd_histogram", 0.0)
    cross = features.get("macd_crossover", 0.0)
    if cross > 0 and hist > 0:
        return RawSignal("", "", "BUY", min(1.0, abs(hist) * 200), ["macd_histogram", "macd_crossover"])
    if cross < 0 and hist < 0:
        return RawSignal("", "", "SELL", min(1.0, abs(hist) * 200), ["macd_histogram", "macd_crossover"])
    return None


def _rule_bb_reversion(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """Bollinger Band mean reversion."""
    pos = features.get("bb_position", 0.5)
    rsi = features.get("rsi_14", 50.0)
    hurst = features.get("hurst", 0.5)
    if hurst > 0.55:   # trending — don't fade
        return None
    if pos < 0.10 and rsi < 40:
        strength = (0.15 - pos) / 0.15
        return RawSignal("", "", "BUY", min(1.0, strength), ["bb_position", "rsi_14", "hurst"])
    if pos > 0.90 and rsi > 60:
        strength = (pos - 0.85) / 0.15
        return RawSignal("", "", "SELL", min(1.0, strength), ["bb_position", "rsi_14", "hurst"])
    return None


def _rule_volatility_breakout(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """Keltner squeeze breakout."""
    squeeze = features.get("kc_squeeze", 0.0)
    momentum = features.get("momentum_20", 0.0)
    volume_z = features.get("volume_zscore_20", 0.0)
    if squeeze < 1.0:  # not in squeeze
        return None
    if momentum > 0 and volume_z > 1.5:
        return RawSignal("", "", "BUY", min(1.0, volume_z * 0.3), ["kc_squeeze", "momentum_20", "volume_zscore_20"])
    if momentum < 0 and volume_z > 1.5:
        return RawSignal("", "", "SELL", min(1.0, volume_z * 0.3), ["kc_squeeze", "momentum_20", "volume_zscore_20"])
    return None


def _rule_trend_alignment(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """Multi-MA trend alignment score."""
    alignment = features.get("trend_alignment", 0.0)
    momentum = features.get("momentum_60", 0.0)
    sharpe = features.get("sharpe_rolling_60", 0.0)
    threshold = float(params.get("alignment_threshold", 0.6))
    if alignment >= threshold and momentum > 0 and sharpe > 0.5:
        return RawSignal("", "", "BUY", alignment, ["trend_alignment", "momentum_60", "sharpe_rolling_60"])
    if alignment <= -threshold and momentum < 0 and sharpe > 0.5:
        return RawSignal("", "", "SELL", abs(alignment), ["trend_alignment", "momentum_60", "sharpe_rolling_60"])
    return None


def _rule_volume_confirmation(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """Volume-confirmed momentum."""
    vol_z = features.get("volume_zscore_20", 0.0)
    cmf = features.get("cmf_21", 0.0)
    obv_z = features.get("obv_zscore_20", 0.0)
    roc = features.get("roc_10", 0.0)
    spike_thresh = float(params.get("spike_threshold", 1.5))
    if vol_z > spike_thresh and cmf > 0.05 and roc > 0:
        strength = min(1.0, (vol_z - spike_thresh) * 0.4 + cmf * 2)
        return RawSignal("", "", "BUY", strength, ["volume_zscore_20", "cmf_21", "roc_10"])
    if vol_z > spike_thresh and cmf < -0.05 and roc < 0:
        strength = min(1.0, (vol_z - spike_thresh) * 0.4 + abs(cmf) * 2)
        return RawSignal("", "", "SELL", strength, ["volume_zscore_20", "cmf_21", "roc_10"])
    return None


def _rule_stat_arb_zscore(features: Dict[str, float], params: Dict[str, Any]) -> Optional[RawSignal]:
    """Statistical z-score reversion."""
    pz = features.get("price_zscore_20", 0.0)
    autocorr = features.get("autocorr_lag1", 0.0)
    hurst = features.get("hurst", 0.5)
    entry_z = float(params.get("entry_zscore", 2.0))
    if hurst > 0.5 or autocorr > 0:   # trending / positive autocorr — skip
        return None
    if pz < -entry_z:
        return RawSignal("", "", "BUY", min(1.0, abs(pz) / entry_z * 0.5), ["price_zscore_20", "hurst", "autocorr_lag1"])
    if pz > entry_z:
        return RawSignal("", "", "SELL", min(1.0, abs(pz) / entry_z * 0.5), ["price_zscore_20", "hurst", "autocorr_lag1"])
    return None


# Rule registry: strategy_type → rule function
SIGNAL_RULES: Dict[str, Callable] = {
    "ema_cross":          _rule_ema_cross,
    "rsi_threshold":      _rule_rsi_threshold,
    "macd_histogram":     _rule_macd_histogram,
    "bb_reversion":       _rule_bb_reversion,
    "volatility_breakout": _rule_volatility_breakout,
    "trend_alignment":    _rule_trend_alignment,
    "volume_confirmation": _rule_volume_confirmation,
    "stat_arb_zscore":    _rule_stat_arb_zscore,
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class StrategySignalConfig:
    """Configures one strategy's signal generation."""

    def __init__(
        self,
        strategy_id: str,
        rule_type: str,
        symbols: List[str],
        timeframe: str = "5m",
        params: Optional[Dict[str, Any]] = None,
        min_strength: float = 0.1,
    ) -> None:
        self.strategy_id = strategy_id
        self.rule_type = rule_type
        self.symbols = symbols
        self.timeframe = timeframe
        self.params = params or {}
        self.min_strength = min_strength


class SignalGeneratorEngine:
    """
    Generates raw signals across all registered strategies and symbols.

    Integration with FeatureEngineeringEngine:
        gen = SignalGeneratorEngine(feature_store=store)
        gen.register(StrategySignalConfig("trend_1", "ema_cross", ["NSE:SBIN-EQ"]))
        signals = gen.generate_all(feature_engine=feat_eng, symbols=[...])
    """

    def __init__(
        self,
        feature_store: Optional[FeatureStore] = None,
        min_strength_global: float = 0.05,
    ) -> None:
        self._store = feature_store or FeatureStore()
        self._configs: Dict[str, StrategySignalConfig] = {}
        self._min_strength = min_strength_global

    def register(self, config: StrategySignalConfig) -> None:
        self._configs[config.strategy_id] = config

    def register_many(self, configs: List[StrategySignalConfig]) -> None:
        for c in configs:
            self.register(c)

    def unregister(self, strategy_id: str) -> None:
        self._configs.pop(strategy_id, None)

    def generate_all(
        self,
        feature_snapshots: Optional[List[Dict[str, Any]]] = None,
        feature_engine: Optional[Any] = None,
        symbols: Optional[List[str]] = None,
        timeframe: str = "5m",
        regime: str = "UNKNOWN",
    ) -> List[RawSignal]:
        """
        Generate signals for all registered strategies.
        Accepts either pre-computed snapshots or a live feature engine.
        """
        if not self._configs:
            return []

        # Build feature map: symbol → features dict
        feat_map: Dict[str, Dict[str, float]] = {}

        if feature_snapshots:
            for snap in feature_snapshots:
                sym = str(snap.get("symbol", ""))
                if sym:
                    feat_map[sym] = dict(snap.get("features", {}))

        if feature_engine and symbols:
            for sym in symbols:
                if sym not in feat_map:
                    snap = feature_engine.compute(sym, timeframe, persist=False)
                    if snap:
                        feat_map[sym] = snap.features

        signals: List[RawSignal] = []
        for strat_id, cfg in self._configs.items():
            rule_fn = SIGNAL_RULES.get(cfg.rule_type)
            if rule_fn is None:
                continue
            for sym in cfg.symbols:
                features = feat_map.get(sym)
                if not features:
                    continue
                try:
                    sig = rule_fn(features, cfg.params)
                except Exception:
                    continue
                if sig is None:
                    continue
                sig.strategy_id = strat_id
                sig.symbol = sym
                sig.timeframe = cfg.timeframe
                sig.regime_hint = regime
                if sig.strength < max(self._min_strength, cfg.min_strength):
                    continue
                signals.append(sig)

        return signals

    def generate_for_strategy(
        self,
        strategy_id: str,
        features: Dict[str, float],
        symbol: str,
        regime: str = "UNKNOWN",
    ) -> Optional[RawSignal]:
        """Generate a signal for one strategy/symbol pair with pre-fetched features."""
        cfg = self._configs.get(strategy_id)
        if not cfg:
            return None
        rule_fn = SIGNAL_RULES.get(cfg.rule_type)
        if not rule_fn:
            return None
        try:
            sig = rule_fn(features, cfg.params)
        except Exception:
            return None
        if sig is None:
            return None
        sig.strategy_id = strategy_id
        sig.symbol = symbol
        sig.regime_hint = regime
        return sig if sig.strength >= self._min_strength else None

    def available_rules(self) -> List[str]:
        return list(SIGNAL_RULES.keys())

    def registered_strategies(self) -> List[str]:
        return list(self._configs.keys())

    def stats(self) -> Dict[str, Any]:
        return {
            "registered_strategies": len(self._configs),
            "available_rules": len(SIGNAL_RULES),
        }
