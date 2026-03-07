"""
quant_ecosystem/research_memory/performance_archive.py
=======================================================
Performance Archive — Quant Ecosystem 3.0

Long-term, regime-aware storage of strategy performance across every phase
of a strategy's lifecycle: backtest, shadow, paper, live, retired.

Institutional quant funds keep permanent performance archives because:
• Past performance in specific regimes guides future deployment decisions.
• Comparing live vs backtest metrics reveals over-fitting and regime breaks.
• Cross-strategy correlation monitoring prevents portfolio concentration.

Architecture
------------
PerformanceSlice   — one time-boxed performance snapshot (e.g. "Q1 2026 live")
RegimePerformance  — per-regime performance summary for one strategy
StrategyArchive    — complete performance history for one strategy
PerformanceArchive — system-wide archive (one StrategyArchive per strategy_id)

Storage layout
--------------
    <root>/performance_archive/
        <strategy_id>/
            archive.json       — full StrategyArchive (latest)
            slices.jsonl       — append-only log of every slice

Integration points
------------------
• shadow_trading.ShadowPerformanceTracker  — call archive.add_slice() on each cycle
• research.PerformanceStore                — bridge existing in-memory records here
• strategy_selector.SelectorCore          — call archive.regime_stats() for selection
• strategy_survival.SurvivalEngine        — call archive.deterioration_score() for retirement
"""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass
class PerformanceSlice:
    """
    Performance over a bounded time window for one strategy in one regime.

    A strategy accumulates many slices as it moves through regimes over time.
    """

    # --- Identity ---
    strategy_id:    str
    slice_id:       str         = ""            # auto-generated on creation
    phase:          str         = "backtest"    # backtest|shadow|paper|live|retired
    regime:         str         = "all"
    asset_class:    str         = "EQUITY"

    # --- Time window ---
    start_date:     str         = ""
    end_date:       str         = ""
    trade_count:    int         = 0

    # --- Core metrics ---
    sharpe:         float       = 0.0
    sortino:        float       = 0.0
    calmar:         float       = 0.0
    drawdown:       float       = 0.0       # max drawdown, negative
    win_rate:       float       = 0.0
    profit_factor:  float       = 0.0
    expectancy:     float       = 0.0
    daily_pnl:      float       = 0.0
    total_pnl:      float       = 0.0
    turnover:       float       = 0.0

    # --- Risk-adjusted ---
    var_95:         float       = 0.0       # Value at Risk 95%
    cvar_95:        float       = 0.0       # Conditional VaR 95%

    # --- Free-form ---
    notes:          str         = ""
    created_at:     str         = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "PerformanceSlice":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class RegimePerformance:
    """
    Aggregated performance of one strategy across all slices in one regime.
    """
    strategy_id:    str
    regime:         str
    slice_count:    int         = 0
    total_trades:   int         = 0
    avg_sharpe:     float       = 0.0
    best_sharpe:    float       = 0.0
    worst_sharpe:   float       = 0.0
    avg_drawdown:   float       = 0.0
    worst_drawdown: float       = 0.0
    avg_win_rate:   float       = 0.0
    avg_profit_factor: float    = 0.0
    total_pnl:      float       = 0.0
    consistency:    float       = 0.0   # fraction of slices with positive Sharpe

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StrategyArchive:
    """
    Complete performance history for one strategy across all phases and regimes.
    """
    strategy_id:    str
    family:         str                     = "unknown"
    created_at:     str                     = ""
    updated_at:     str                     = ""
    current_status: str                     = "discovered"
    slices:         List[PerformanceSlice]  = field(default_factory=list)
    regime_stats:   Dict[str, Dict]         = field(default_factory=dict)

    def compute_regime_stats(self) -> Dict[str, RegimePerformance]:
        """Recompute regime-level aggregates from slices."""
        by_regime: Dict[str, List[PerformanceSlice]] = {}
        for s in self.slices:
            by_regime.setdefault(s.regime, []).append(s)

        result: Dict[str, RegimePerformance] = {}
        for regime, slices in by_regime.items():
            sharpes = [s.sharpe for s in slices]
            dds     = [s.drawdown for s in slices]
            pfs     = [s.profit_factor for s in slices if s.profit_factor > 0]
            rp = RegimePerformance(
                strategy_id     = self.strategy_id,
                regime          = regime,
                slice_count     = len(slices),
                total_trades    = sum(s.trade_count for s in slices),
                avg_sharpe      = round(sum(sharpes) / len(sharpes), 4) if sharpes else 0.0,
                best_sharpe     = round(max(sharpes), 4) if sharpes else 0.0,
                worst_sharpe    = round(min(sharpes), 4) if sharpes else 0.0,
                avg_drawdown    = round(sum(dds) / len(dds), 4) if dds else 0.0,
                worst_drawdown  = round(min(dds), 4) if dds else 0.0,
                avg_win_rate    = round(sum(s.win_rate for s in slices) / len(slices), 4) if slices else 0.0,
                avg_profit_factor = round(sum(pfs) / len(pfs), 4) if pfs else 0.0,
                total_pnl       = round(sum(s.total_pnl for s in slices), 4),
                consistency     = round(sum(1 for s in slices if s.sharpe > 0) / len(slices), 4) if slices else 0.0,
            )
            result[regime] = rp
            self.regime_stats[regime] = rp.to_dict()
        return result

    def live_performance(self) -> Optional[PerformanceSlice]:
        live = [s for s in self.slices if s.phase == "live"]
        if not live:
            return None
        return max(live, key=lambda s: s.created_at)

    def backtest_performance(self) -> Optional[PerformanceSlice]:
        bt = [s for s in self.slices if s.phase == "backtest"]
        if not bt:
            return None
        return max(bt, key=lambda s: s.trade_count)

    def deterioration_score(self) -> float:
        """
        Measure how much live performance has deteriorated vs backtest.
        Score < 0 means live is worse than expected.
        Score of -0.5 = live Sharpe is 50% lower than backtest Sharpe.
        """
        live = self.live_performance()
        bt   = self.backtest_performance()
        if live is None or bt is None or bt.sharpe <= 0:
            return 0.0
        return round((live.sharpe - bt.sharpe) / bt.sharpe, 4)

    def to_dict(self) -> Dict:
        d = {
            "strategy_id":    self.strategy_id,
            "family":         self.family,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "current_status": self.current_status,
            "slices":         [s.to_dict() for s in self.slices],
            "regime_stats":   self.regime_stats,
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> "StrategyArchive":
        slices = [PerformanceSlice.from_dict(s) for s in d.get("slices", [])]
        return cls(
            strategy_id    = d.get("strategy_id", ""),
            family         = d.get("family", "unknown"),
            created_at     = d.get("created_at", ""),
            updated_at     = d.get("updated_at", ""),
            current_status = d.get("current_status", "discovered"),
            slices         = slices,
            regime_stats   = d.get("regime_stats", {}),
        )


# ---------------------------------------------------------------------------
# PerformanceArchive
# ---------------------------------------------------------------------------

_NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
_SLICE_SEQ = 0
_SLICE_LOCK = threading.Lock()


def _next_slice_id(strategy_id: str) -> str:
    global _SLICE_SEQ
    with _SLICE_LOCK:
        _SLICE_SEQ += 1
        return f"{strategy_id}_slice_{int(time.time())}_{_SLICE_SEQ:04d}"


class PerformanceArchive:
    """
    System-wide performance archive.

    Quick-start
    -----------
        archive = PerformanceArchive(root="data/performance_archive")

        # Add a backtest slice
        archive.add_slice(PerformanceSlice(
            strategy_id   = "ema_trend_015",
            phase         = "backtest",
            regime        = "trending",
            sharpe        = 1.94,
            drawdown      = -7.2,
            profit_factor = 1.85,
            win_rate      = 56.0,
            trade_count   = 112,
            start_date    = "2023-01-01",
            end_date      = "2025-12-31",
        ))

        # Query regime stats
        stats = archive.regime_stats("ema_trend_015", regime="trending")

        # Get deterioration score (live vs backtest)
        score = archive.deterioration_score("ema_trend_015")

        # Best strategies for a given regime
        top = archive.top_strategies_for_regime("trending", n=5)
    """

    def __init__(
        self,
        root:   str = "data/performance_archive",
        config: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        if config and isinstance(config, dict):
            root = config.get("PERFORMANCE_ARCHIVE_ROOT", root)

        self._root  = Path(root)
        self._lock  = threading.RLock()
        self._cache: Dict[str, StrategyArchive] = {}

        self._root.mkdir(parents=True, exist_ok=True)
        self._rebuild_cache()

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def add_slice(self, sl: PerformanceSlice) -> PerformanceSlice:
        """Persist a performance slice and update aggregates."""
        with self._lock:
            if not sl.slice_id:
                sl.slice_id   = _next_slice_id(sl.strategy_id)
            if not sl.created_at:
                sl.created_at = _NOW()

            arch = self._get_or_create(sl.strategy_id)
            arch.slices.append(sl)
            arch.updated_at = _NOW()
            arch.compute_regime_stats()

            self._write_archive(arch)
            self._append_slice_log(sl)
            return sl

    def add_slice_from_dict(self, d: Dict) -> PerformanceSlice:
        return self.add_slice(PerformanceSlice.from_dict(d))

    def bridge_from_performance_store(
        self,
        strategy_id: str,
        metrics:     Dict[str, float],
        phase:       str = "live",
        regime:      str = "all",
    ) -> PerformanceSlice:
        """
        Bridge an existing PerformanceStore.metrics() dict into the archive.
        Called by strategy_survival or shadow_trading to persist in-memory stats.
        """
        sl = PerformanceSlice(
            strategy_id   = strategy_id,
            phase         = phase,
            regime        = regime,
            sharpe        = metrics.get("sharpe",        0.0),
            drawdown      = -abs(metrics.get("drawdown", 0.0)),
            win_rate      = metrics.get("win_rate",       0.0),
            profit_factor = metrics.get("profit_factor", 0.0),
            daily_pnl     = metrics.get("daily_pnl",     0.0),
        )
        return self.add_slice(sl)

    def update_status(self, strategy_id: str, status: str) -> None:
        with self._lock:
            arch = self._cache.get(strategy_id)
            if arch:
                arch.current_status = status
                arch.updated_at     = _NOW()
                self._write_archive(arch)

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get_archive(self, strategy_id: str) -> Optional[StrategyArchive]:
        return self._cache.get(strategy_id)

    def regime_stats(
        self,
        strategy_id: str,
        regime: Optional[str] = None,
    ) -> Dict[str, Any]:
        arch = self._cache.get(strategy_id)
        if arch is None:
            return {}
        if regime:
            return arch.regime_stats.get(regime, {})
        return arch.regime_stats

    def deterioration_score(self, strategy_id: str) -> float:
        arch = self._cache.get(strategy_id)
        return arch.deterioration_score() if arch else 0.0

    def top_strategies_for_regime(
        self,
        regime:    str,
        phase:     str  = "live",
        n:         int  = 10,
        min_trades: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Return top N strategies ranked by avg Sharpe in a given regime.
        Filters to strategies that have enough live trade history.
        """
        results = []
        for sid, arch in self._cache.items():
            slices = [
                s for s in arch.slices
                if s.regime == regime and s.phase == phase and s.trade_count >= min_trades
            ]
            if not slices:
                continue
            avg_sharpe = sum(s.sharpe for s in slices) / len(slices)
            results.append({
                "strategy_id": sid,
                "family":      arch.family,
                "avg_sharpe":  round(avg_sharpe, 4),
                "slice_count": len(slices),
                "total_trades": sum(s.trade_count for s in slices),
            })
        results.sort(key=lambda x: x["avg_sharpe"], reverse=True)
        return results[:n]

    def cross_strategy_correlation(self, strategy_ids: List[str]) -> Dict[str, float]:
        """
        Compute pairwise average Sharpe correlation between strategies.
        Returns a flat dict: "{sid_a}:{sid_b}" → correlation coefficient.
        Uses regime performance vectors as proxy for returns.
        """
        vectors: Dict[str, Dict[str, float]] = {}
        all_regimes: set = set()

        for sid in strategy_ids:
            arch = self._cache.get(sid)
            if arch is None:
                continue
            vec = {r: float(v.get("avg_sharpe", 0)) for r, v in arch.regime_stats.items()}
            vectors[sid] = vec
            all_regimes.update(vec.keys())

        regimes = sorted(all_regimes)
        corrs: Dict[str, float] = {}

        for i, a in enumerate(strategy_ids):
            for b in strategy_ids[i + 1:]:
                va = [vectors.get(a, {}).get(r, 0.0) for r in regimes]
                vb = [vectors.get(b, {}).get(r, 0.0) for r in regimes]
                corrs[f"{a}:{b}"] = _pearson(va, vb)

        return corrs

    def system_summary(self) -> Dict[str, Any]:
        """High-level summary of the entire archive."""
        all_archives = list(self._cache.values())
        if not all_archives:
            return {"total_strategies": 0}

        all_sharpes = []
        for arch in all_archives:
            for sl in arch.slices:
                if sl.sharpe > 0:
                    all_sharpes.append(sl.sharpe)

        live_strats = [a for a in all_archives if a.current_status == "live"]

        return {
            "total_strategies":  len(all_archives),
            "live_strategies":   len(live_strats),
            "total_slices":      sum(len(a.slices) for a in all_archives),
            "avg_sharpe_all":    round(sum(all_sharpes) / len(all_sharpes), 4) if all_sharpes else 0.0,
            "regimes_covered":   list({s.regime for a in all_archives for s in a.slices}),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, strategy_id: str) -> StrategyArchive:
        if strategy_id not in self._cache:
            arch = StrategyArchive(
                strategy_id = strategy_id,
                created_at  = _NOW(),
                updated_at  = _NOW(),
            )
            self._cache[strategy_id] = arch
            (self._root / strategy_id).mkdir(exist_ok=True)
        return self._cache[strategy_id]

    def _write_archive(self, arch: StrategyArchive) -> None:
        strat_dir = self._root / arch.strategy_id
        strat_dir.mkdir(exist_ok=True)
        path = strat_dir / "archive.json"
        tmp  = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(arch.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)

    def _append_slice_log(self, sl: PerformanceSlice) -> None:
        strat_dir = self._root / sl.strategy_id
        strat_dir.mkdir(exist_ok=True)
        log_path = strat_dir / "slices.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sl.to_dict()) + "\n")

    def _rebuild_cache(self) -> None:
        for strat_dir in sorted(self._root.iterdir()):
            if not strat_dir.is_dir():
                continue
            arch_path = strat_dir / "archive.json"
            if arch_path.exists():
                try:
                    arch = StrategyArchive.from_dict(
                        json.loads(arch_path.read_text(encoding="utf-8"))
                    )
                    self._cache[arch.strategy_id] = arch
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Math helper
# ---------------------------------------------------------------------------

def _pearson(a: List[float], b: List[float]) -> float:
    """Pearson correlation coefficient; returns 0.0 if undefined."""
    n = len(a)
    if n < 2:
        return 0.0
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num  = sum((ai - mean_a) * (bi - mean_b) for ai, bi in zip(a, b))
    den  = math.sqrt(
        sum((ai - mean_a) ** 2 for ai in a) *
        sum((bi - mean_b) ** 2 for bi in b)
    )
    return round(num / den, 6) if den > 1e-9 else 0.0
