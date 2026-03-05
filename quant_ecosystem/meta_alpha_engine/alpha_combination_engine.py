"""
alpha_combination_engine.py
Combines signals from multiple alpha sources into a single meta-signal per symbol.
Supports: mean combination, IC-weighted, rank-weighted, and PCA-based combination.
This is the core of the meta-alpha layer — akin to how Renaissance blends sub-models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from quant_ecosystem.signal_factory.signal_generator_engine import RawSignal
from quant_ecosystem.signal_factory.signal_quality_engine import SignalQualityEngine


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class MetaSignal:
    """Combined signal from multiple alpha sources."""
    symbol: str
    side: str                        # BUY | SELL | HOLD
    combined_strength: float         # [0, 1]
    n_contributors: int              # how many alphas agreed
    agreement_rate: float            # fraction of contributors on same side
    method: str                      # combination method used
    source_signals: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "combined_strength": round(self.combined_strength, 6),
            "n_contributors": self.n_contributors,
            "agreement_rate": round(self.agreement_rate, 4),
            "method": self.method,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Combination methods
# ---------------------------------------------------------------------------

def _side_score(side: str) -> float:
    return 1.0 if side == "BUY" else -1.0 if side == "SELL" else 0.0


def _mean_combination(
    signals: List[RawSignal],
    weights: Optional[Dict[str, float]] = None,
) -> MetaSignal:
    """Simple (optionally weighted) mean of signed strengths."""
    sym = signals[0].symbol
    scores = []
    for s in signals:
        w = weights.get(s.strategy_id, 1.0) if weights else 1.0
        scores.append(_side_score(s.side) * s.strength * w)

    total_w = sum(weights.get(s.strategy_id, 1.0) for s in signals) if weights else len(signals)
    net = sum(scores) / total_w if total_w > 0 else 0.0
    side = "BUY" if net > 0.05 else "SELL" if net < -0.05 else "HOLD"
    agree_sigs = [s for s in signals if str(s.side) == side]
    agreement = len(agree_sigs) / len(signals)
    return MetaSignal(
        symbol=sym, side=side,
        combined_strength=round(min(1.0, abs(net)), 6),
        n_contributors=len(signals),
        agreement_rate=round(agreement, 4),
        method="mean",
        source_signals=[s.to_dict() for s in signals],
    )


def _ic_weighted_combination(
    signals: List[RawSignal],
    quality_engine: SignalQualityEngine,
) -> MetaSignal:
    """Weight each signal by its Information Coefficient."""
    ic_weights: Dict[str, float] = {}
    for s in signals:
        stats = quality_engine.compute_stats(s.strategy_id)
        ic_weights[s.strategy_id] = max(0.0, stats.ic)

    total_ic = sum(ic_weights.values())
    if total_ic == 0:
        # No IC data — fall back to equal weight
        return _mean_combination(signals, weights=None)

    return _mean_combination(signals, weights={k: v / total_ic for k, v in ic_weights.items()})


def _rank_weighted_combination(signals: List[RawSignal]) -> MetaSignal:
    """Rank signals by strength; assign rank-proportional weights."""
    ranked = sorted(signals, key=lambda s: s.strength, reverse=True)
    n = len(ranked)
    weights = {s.strategy_id: (n - i) / n for i, s in enumerate(ranked)}
    return _mean_combination(ranked, weights=weights)


def _majority_vote_combination(signals: List[RawSignal]) -> MetaSignal:
    """Pure majority vote: side with more votes wins, strength = vote margin."""
    sym = signals[0].symbol
    buy_votes = sum(1 for s in signals if s.side == "BUY")
    sell_votes = sum(1 for s in signals if s.side == "SELL")
    total = len(signals)
    if buy_votes > sell_votes:
        side = "BUY"
        strength = (buy_votes - sell_votes) / total
        agreement = buy_votes / total
    elif sell_votes > buy_votes:
        side = "SELL"
        strength = (sell_votes - buy_votes) / total
        agreement = sell_votes / total
    else:
        side = "HOLD"
        strength = 0.0
        agreement = 0.5
    return MetaSignal(
        symbol=sym, side=side,
        combined_strength=round(strength, 6),
        n_contributors=total,
        agreement_rate=round(agreement, 4),
        method="majority_vote",
        source_signals=[s.to_dict() for s in signals],
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AlphaCombinationEngine:
    """
    Combines per-strategy signals into meta-signals per symbol.

    Usage:
        engine = AlphaCombinationEngine(method="ic_weighted", quality_engine=sqe)
        meta_signals = engine.combine(raw_signals)

    Methods: "mean" | "ic_weighted" | "rank_weighted" | "majority_vote" | "regime_adaptive"
    """

    def __init__(
        self,
        method: str = "ic_weighted",
        quality_engine: Optional[SignalQualityEngine] = None,
        min_contributors: int = 1,
        min_agreement: float = 0.0,
        regime: str = "UNKNOWN",
    ) -> None:
        self._method = str(method).lower()
        self._quality_engine = quality_engine or SignalQualityEngine()
        self._min_contributors = max(1, int(min_contributors))
        self._min_agreement = float(min_agreement)
        self._regime = str(regime).upper()

    def update_regime(self, regime: str) -> None:
        self._regime = str(regime).upper()

    def combine(self, signals: List[RawSignal]) -> List[MetaSignal]:
        """Combine signals — produces one MetaSignal per symbol."""
        by_symbol: Dict[str, List[RawSignal]] = {}
        for s in signals:
            by_symbol.setdefault(s.symbol, []).append(s)

        results: List[MetaSignal] = []
        for sym, sym_signals in by_symbol.items():
            if len(sym_signals) < self._min_contributors:
                continue
            meta = self._combine_symbol(sym_signals)
            if meta.agreement_rate < self._min_agreement:
                continue
            if meta.side == "HOLD":
                continue
            results.append(meta)

        # Sort by combined_strength descending
        results.sort(key=lambda m: m.combined_strength, reverse=True)
        return results

    def combine_single_symbol(
        self, symbol: str, signals: List[RawSignal]
    ) -> Optional[MetaSignal]:
        """Combine signals for one specific symbol."""
        sym_signals = [s for s in signals if s.symbol == symbol]
        if not sym_signals:
            return None
        return self._combine_symbol(sym_signals)

    def _combine_symbol(self, signals: List[RawSignal]) -> MetaSignal:
        method = self._effective_method()
        if method == "ic_weighted":
            return _ic_weighted_combination(signals, self._quality_engine)
        if method == "rank_weighted":
            return _rank_weighted_combination(signals)
        if method == "majority_vote":
            return _majority_vote_combination(signals)
        return _mean_combination(signals)

    def _effective_method(self) -> str:
        """Adapt method based on regime for regime_adaptive mode."""
        if self._method != "regime_adaptive":
            return self._method
        # In trending regimes, rank-weighted follows strong signals best
        if self._regime in ("TRENDING_BULL", "TRENDING_BEAR", "TREND"):
            return "rank_weighted"
        # In ranging, IC-weighted is better (quality matters more)
        if self._regime in ("RANGE_BOUND", "LOW_VOLATILITY", "MEAN_REVERSION"):
            return "ic_weighted"
        # In volatile regimes, majority vote to reduce noise
        if self._regime in ("HIGH_VOLATILITY", "CRASH_EVENT"):
            return "majority_vote"
        return "mean"

    def set_method(self, method: str) -> None:
        self._method = str(method).lower()

    def stats(self) -> Dict[str, Any]:
        return {
            "method": self._method,
            "effective_method": self._effective_method(),
            "min_contributors": self._min_contributors,
            "regime": self._regime,
        }
