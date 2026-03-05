"""
signal_quality_engine.py
Evaluates signal quality using information coefficient (IC), information ratio (IR),
hit rate, signal decay analysis, and Spearman rank correlation.
Used to rank and prune strategy signals before execution.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

from quant_ecosystem.signal_factory.signal_generator_engine import RawSignal


@dataclass
class SignalRecord:
    """Tracks a signal outcome once the forward return is known."""
    strategy_id: str
    symbol: str
    side: str
    strength: float
    timestamp: float
    forward_return: Optional[float] = None       # pct return N bars later
    realized_pnl: Optional[float] = None
    correct_direction: Optional[bool] = None


@dataclass
class StrategySignalStats:
    """Aggregated signal quality metrics for one strategy."""
    strategy_id: str
    ic: float = 0.0          # Information Coefficient (Spearman rank)
    ir: float = 0.0          # Information Ratio = IC / std(IC)
    hit_rate: float = 0.0    # fraction of signals with correct direction
    avg_forward_return: float = 0.0
    decay_halflife: float = np.inf  # bars until IC halves
    sample_count: int = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "ic": round(self.ic, 6),
            "ir": round(self.ir, 6),
            "hit_rate": round(self.hit_rate, 6),
            "avg_forward_return": round(self.avg_forward_return, 6),
            "decay_halflife": round(self.decay_halflife, 2) if np.isfinite(self.decay_halflife) else None,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated,
        }


@dataclass
class QualifiedSignal:
    """A RawSignal augmented with quality metadata."""
    signal: RawSignal
    quality_score: float         # [0, 1] composite quality
    ic_score: float
    ir_score: float
    hit_rate: float
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = self.signal.to_dict()
        d["quality_score"] = round(self.quality_score, 6)
        d["ic_score"] = round(self.ic_score, 6)
        d["ir_score"] = round(self.ir_score, 6)
        d["hit_rate"] = round(self.hit_rate, 6)
        d["rank"] = self.rank
        return d


class SignalQualityEngine:
    """
    Tracks signal outcomes and computes quality metrics per strategy.

    Lifecycle:
      1. emit(signal)                — record a signal being generated
      2. resolve(strategy_id, symbol, forward_return)  — update with realized return
      3. score(signals)             — annotate live signals with quality scores
      4. rank(signals)              — sort by quality, return QualifiedSignals

    Usage:
        sqe = SignalQualityEngine()
        sqe.emit(raw_signal)
        sqe.resolve("trend_1", "NSE:SBIN-EQ", forward_return=0.012)
        ranked = sqe.rank(new_signals, top_n=5)
    """

    def __init__(
        self,
        max_history: int = 1000,
        min_ic_threshold: float = 0.03,
        ic_window: int = 60,
    ) -> None:
        self._max_history = int(max_history)
        self._min_ic = float(min_ic_threshold)
        self._ic_window = int(ic_window)
        # strategy_id → deque of SignalRecord
        self._records: Dict[str, Deque[SignalRecord]] = {}
        # strategy_id → cached stats
        self._stats: Dict[str, StrategySignalStats] = {}
        # pending: (strategy_id, symbol, ts) → SignalRecord
        self._pending: Dict[Tuple[str, str, float], SignalRecord] = {}

    # ------------------------------------------------------------------
    # Intake and resolution
    # ------------------------------------------------------------------

    def emit(self, signal: RawSignal) -> None:
        """Record a signal that was generated (before outcome known)."""
        key = (signal.strategy_id, signal.symbol, signal.timestamp)
        rec = SignalRecord(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=signal.side,
            strength=signal.strength,
            timestamp=signal.timestamp,
        )
        self._pending[key] = rec

    def resolve(
        self,
        strategy_id: str,
        symbol: str,
        forward_return: float,
        timestamp: Optional[float] = None,
    ) -> None:
        """Mark a pending signal's outcome with its realized forward return."""
        # Find the most recent pending signal for this (strategy, symbol)
        candidates = [
            (k, v) for k, v in self._pending.items()
            if k[0] == strategy_id and k[1] == symbol
        ]
        if not candidates:
            return
        # Resolve most recent
        key, rec = max(candidates, key=lambda x: x[0][2])
        del self._pending[key]

        rec.forward_return = float(forward_return)
        direction_multiplier = 1.0 if rec.side == "BUY" else -1.0
        rec.correct_direction = (forward_return * direction_multiplier) > 0
        rec.realized_pnl = forward_return * direction_multiplier

        if strategy_id not in self._records:
            self._records[strategy_id] = deque(maxlen=self._max_history)
        self._records[strategy_id].append(rec)

        # Invalidate cached stats
        self._stats.pop(strategy_id, None)

    def resolve_batch(
        self, outcomes: List[Dict[str, Any]]
    ) -> None:
        """Batch resolve: each dict has {strategy_id, symbol, forward_return}."""
        for row in outcomes:
            self.resolve(
                str(row.get("strategy_id", "")),
                str(row.get("symbol", "")),
                float(row.get("forward_return", 0.0)),
            )

    # ------------------------------------------------------------------
    # Quality computation
    # ------------------------------------------------------------------

    def compute_stats(self, strategy_id: str) -> StrategySignalStats:
        """Compute and cache quality stats for one strategy."""
        if strategy_id in self._stats:
            return self._stats[strategy_id]

        records = list(self._records.get(strategy_id, []))
        resolved = [r for r in records if r.forward_return is not None]

        if len(resolved) < 5:
            stats = StrategySignalStats(strategy_id=strategy_id, sample_count=len(resolved))
            self._stats[strategy_id] = stats
            return stats

        strengths = np.array([r.strength for r in resolved], dtype=np.float64)
        forward_rets = np.array([r.forward_return * (1 if r.side == "BUY" else -1)
                                  for r in resolved], dtype=np.float64)

        ic = self._spearman_ic(strengths, forward_rets)
        ir = self._information_ratio(resolved, window=self._ic_window)
        hit = float(sum(1 for r in resolved if r.correct_direction) / len(resolved))
        avg_ret = float(np.mean(forward_rets))
        halflife = self._decay_halflife(resolved)

        stats = StrategySignalStats(
            strategy_id=strategy_id,
            ic=float(ic),
            ir=float(ir),
            hit_rate=hit,
            avg_forward_return=avg_ret,
            decay_halflife=halflife,
            sample_count=len(resolved),
            last_updated=time.time(),
        )
        self._stats[strategy_id] = stats
        return stats

    def score(self, signals: List[RawSignal]) -> List[QualifiedSignal]:
        """Annotate each signal with quality scores from its strategy's history."""
        qualified = []
        for sig in signals:
            stats = self.compute_stats(sig.strategy_id)
            quality = self._composite_quality(stats, sig)
            qualified.append(QualifiedSignal(
                signal=sig,
                quality_score=quality,
                ic_score=max(0.0, stats.ic),
                ir_score=max(0.0, stats.ir),
                hit_rate=stats.hit_rate,
            ))
        return qualified

    def rank(
        self,
        signals: List[RawSignal],
        top_n: Optional[int] = None,
        min_quality: float = 0.0,
    ) -> List[QualifiedSignal]:
        """Score, filter by min quality, and return top_n ranked signals."""
        qualified = self.score(signals)
        qualified = [q for q in qualified if q.quality_score >= min_quality]
        qualified.sort(key=lambda q: q.quality_score, reverse=True)
        for i, q in enumerate(qualified):
            q.rank = i + 1
        return qualified[:top_n] if top_n else qualified

    def get_stats(self, strategy_id: str) -> Optional[StrategySignalStats]:
        return self.compute_stats(strategy_id)

    def all_stats(self) -> List[StrategySignalStats]:
        all_ids = set(self._records.keys()) | set(self._stats.keys())
        return [self.compute_stats(sid) for sid in all_ids]

    def prune_low_quality(
        self, threshold: float = -0.05, min_samples: int = 30
    ) -> List[str]:
        """Return strategy IDs with IC below threshold (for review/retirement)."""
        pruned = []
        for sid in list(self._records.keys()):
            stats = self.compute_stats(sid)
            if stats.sample_count >= min_samples and stats.ic < threshold:
                pruned.append(sid)
        return pruned

    # ------------------------------------------------------------------
    # Metric computations
    # ------------------------------------------------------------------

    @staticmethod
    def _spearman_ic(
        strengths: np.ndarray, forward_rets: np.ndarray
    ) -> float:
        """Spearman rank correlation between signal strength and forward return."""
        n = len(strengths)
        if n < 5:
            return 0.0
        from scipy.stats import spearmanr
        try:
            corr, _ = spearmanr(strengths, forward_rets)
            return float(corr) if np.isfinite(corr) else 0.0
        except Exception:
            return 0.0

    def _information_ratio(
        self, records: List[SignalRecord], window: int = 60
    ) -> float:
        """IC / std(IC) over rolling window of recent records."""
        resolved = [r for r in records if r.forward_return is not None]
        if len(resolved) < window:
            return 0.0
        # Compute rolling ICs
        ic_series = []
        step = max(1, window // 5)
        for i in range(window, len(resolved) + 1, step):
            chunk = resolved[i - window : i]
            s = np.array([r.strength for r in chunk], dtype=np.float64)
            f = np.array([r.forward_return * (1 if r.side == "BUY" else -1) for r in chunk], dtype=np.float64)
            ic_series.append(self._spearman_ic(s, f))
        if len(ic_series) < 2:
            return 0.0
        arr = np.array(ic_series)
        std = np.std(arr, ddof=1)
        return float(np.mean(arr) / std) if std > 0 else 0.0

    def _decay_halflife(self, records: List[SignalRecord]) -> float:
        """Estimate the time (in periods) until IC decays to half its value."""
        resolved = sorted(
            [r for r in records if r.forward_return is not None],
            key=lambda r: r.timestamp,
        )
        if len(resolved) < 20:
            return np.inf
        # Compute IC at lag 0, lag 5, lag 10, …
        window = min(40, len(resolved) // 2)
        lags = [0, window // 4, window // 2, window]
        ics = []
        for lag in lags:
            chunk = resolved[lag : lag + window]
            if len(chunk) < 5:
                break
            s = np.array([r.strength for r in chunk], dtype=np.float64)
            f = np.array([r.forward_return * (1 if r.side == "BUY" else -1) for r in chunk], dtype=np.float64)
            ics.append(self._spearman_ic(s, f))
        if len(ics) < 2 or ics[0] == 0:
            return np.inf
        # Fit simple exponential decay
        try:
            ratios = [ic / ics[0] for ic in ics[1:] if ics[0] != 0]
            valid = [r for r in ratios if r > 0]
            if not valid:
                return np.inf
            decay_rate = -np.log(np.mean(valid)) / (window / 4)
            return float(np.log(2) / decay_rate) if decay_rate > 0 else np.inf
        except Exception:
            return np.inf

    def _composite_quality(
        self, stats: StrategySignalStats, signal: RawSignal
    ) -> float:
        """Composite quality score: weighted blend of IC, IR, hit rate, strength."""
        if stats.sample_count < 5:
            # New strategy — give neutral score boosted by signal strength
            return signal.strength * 0.4
        ic_norm = max(0.0, min(1.0, (stats.ic + 0.10) / 0.30))     # IC in [-0.1, 0.2] → [0, 1]
        ir_norm = max(0.0, min(1.0, (stats.ir + 1.0) / 3.0))       # IR in [-1, 2] → [0, 1]
        hit_norm = max(0.0, min(1.0, (stats.hit_rate - 0.45) / 0.30))  # hit rate in [0.45, 0.75]
        strength_norm = float(signal.strength)
        quality = (
            0.35 * ic_norm +
            0.25 * ir_norm +
            0.25 * hit_norm +
            0.15 * strength_norm
        )
        return round(float(quality), 6)
