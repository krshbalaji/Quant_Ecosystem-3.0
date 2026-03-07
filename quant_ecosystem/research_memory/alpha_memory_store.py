"""
quant_ecosystem/research_memory/alpha_memory_store.py
======================================================
Persistent Alpha Memory Store — Quant Ecosystem 3.0

Institutional quant funds maintain a permanent record of every alpha signal
ever discovered, including its statistical properties, regime behaviour, and
evolution lineage.  This module provides that capability.

Architecture
------------
AlphaRecord         — immutable value object for one alpha entry
AlphaMemoryIndex    — in-memory index rebuilt from disk on load
AlphaMemoryStore    — primary interface (read / write / query)

Storage
-------
One JSON file per alpha in:
    <store_root>/alphas/<strategy_id>.json

A compact catalogue file for fast scanning:
    <store_root>/alpha_catalogue.jsonl   (append-only JSONL)

Integration points
------------------
• research.alpha_evolution_engine   — call store.record() after each evolution cycle
• research.alpha_discovery_engine   — call store.record() on new discovery
• shadow_trading.shadow_engine      — call store.update_live_stats() on promotion
• strategy_selector.selector_core   — call store.query_by_regime() for regime routing
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Value object
# ---------------------------------------------------------------------------

@dataclass
class AlphaRecord:
    """
    Immutable snapshot of an alpha's identity and statistical profile.

    Fields marked *mutable* are updated in-place (e.g. live_sharpe after
    promotion) — all mutations produce a new record written to disk.
    """

    # --- Identity ---
    strategy_id:    str
    parent_id:      Optional[str]   = None      # None for seed strategies
    generation:     int             = 0         # 0 = seed, N = Nth mutation
    family:         str             = "unknown" # ema_trend, rsi_reversion …

    # --- Regime context ---
    regime:         str             = "all"     # regime it was designed/tested in
    asset_class:    str             = "EQUITY"

    # --- Core alpha statistics (backtest) ---
    sharpe:         float           = 0.0
    drawdown:       float           = 0.0       # negative, e.g. -7.2
    profit_factor:  float           = 0.0
    win_rate:       float           = 0.0
    expectancy:     float           = 0.0
    turnover:       float           = 0.0       # trades per day
    trade_count:    int             = 0

    # --- Live / shadow statistics (post-promotion) ---
    live_sharpe:    float           = 0.0
    live_drawdown:  float           = 0.0
    live_trade_count: int           = 0
    shadow_passed:  bool            = False
    promoted_to_live: bool          = False

    # --- Lifecycle ---
    status:         str             = "discovered"  # discovered | shadow | live | retired
    created_at:     str             = ""
    updated_at:     str             = ""
    retired_at:     str             = ""
    retire_reason:  str             = ""

    # --- Free-form metadata ---
    tags:           List[str]       = field(default_factory=list)
    notes:          str             = ""
    extra:          Dict[str, Any]  = field(default_factory=dict)

    def composite_score(self) -> float:
        """
        Composite quality score used for ranking.

        Score = Sharpe * (1 - |drawdown|/100) * sqrt(min(trade_count, 200)/200)
        Range: typically 0–3.
        """
        s = max(self.sharpe, 0.0)
        dd_penalty = 1.0 - min(abs(self.drawdown) / 100.0, 0.99)
        sample_confidence = math.sqrt(min(self.trade_count, 200) / 200.0) if self.trade_count > 0 else 0.0
        return round(s * dd_penalty * sample_confidence, 6)

    def is_institutional_grade(self) -> bool:
        """Returns True if alpha meets minimum institutional thresholds."""
        return (
            self.sharpe >= 1.0
            and self.drawdown >= -20.0       # drawdown is negative
            and self.profit_factor >= 1.3
            and self.trade_count >= 30
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "AlphaRecord":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Index — fast lookup without reading every file
# ---------------------------------------------------------------------------

class AlphaMemoryIndex:
    """
    In-memory index over AlphaRecords.

    Rebuilt from the JSONL catalogue at startup.
    Updated in-place on every write — O(1) lookups.
    """

    def __init__(self) -> None:
        self._by_id:      Dict[str, AlphaRecord] = {}
        self._by_family:  Dict[str, List[str]]   = {}
        self._by_regime:  Dict[str, List[str]]   = {}
        self._by_status:  Dict[str, List[str]]   = {}

    def add(self, rec: AlphaRecord) -> None:
        sid = rec.strategy_id
        self._by_id[sid] = rec

        self._by_family.setdefault(rec.family, [])
        if sid not in self._by_family[rec.family]:
            self._by_family[rec.family].append(sid)

        self._by_regime.setdefault(rec.regime, [])
        if sid not in self._by_regime[rec.regime]:
            self._by_regime[rec.regime].append(sid)

        self._by_status.setdefault(rec.status, [])
        if sid not in self._by_status[rec.status]:
            self._by_status[rec.status].append(sid)

    def remove(self, strategy_id: str) -> None:
        rec = self._by_id.pop(strategy_id, None)
        if rec:
            self._by_family.get(rec.family, [self._noop])[0]
            for mapping in (self._by_family, self._by_regime, self._by_status):
                for lst in mapping.values():
                    if strategy_id in lst:
                        lst.remove(strategy_id)

    @staticmethod
    def _noop(*_):
        pass

    def get(self, strategy_id: str) -> Optional[AlphaRecord]:
        return self._by_id.get(strategy_id)

    def all_ids(self) -> List[str]:
        return list(self._by_id.keys())

    def by_regime(self, regime: str) -> List[AlphaRecord]:
        ids = self._by_regime.get(regime, []) + self._by_regime.get("all", [])
        return [self._by_id[i] for i in ids if i in self._by_id]

    def by_family(self, family: str) -> List[AlphaRecord]:
        return [self._by_id[i] for i in self._by_family.get(family, []) if i in self._by_id]

    def by_status(self, status: str) -> List[AlphaRecord]:
        return [self._by_id[i] for i in self._by_status.get(status, []) if i in self._by_id]

    def top_n(self, n: int = 10, regime: Optional[str] = None) -> List[AlphaRecord]:
        pool = self.by_regime(regime) if regime else list(self._by_id.values())
        return sorted(pool, key=lambda r: r.composite_score(), reverse=True)[:n]


# ---------------------------------------------------------------------------
# Primary store
# ---------------------------------------------------------------------------

_NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class AlphaMemoryStore:
    """
    Persistent, thread-safe store for all alpha discoveries.

    Usage
    -----
        store = AlphaMemoryStore(root="/path/to/quant_data/alpha_memory")

        # Record a new alpha
        store.record(AlphaRecord(
            strategy_id="ema_trend_015",
            parent_id="ema_trend_011",
            regime="high_volatility",
            sharpe=1.94,
            drawdown=-7.2,
            family="ema_trend",
            trade_count=112,
        ))

        # Query
        top = store.top_alphas(regime="trending", n=5)

        # Update live stats after promotion
        store.update_live_stats("ema_trend_015", live_sharpe=1.71, live_trade_count=23)
    """

    _CATALOGUE   = "alpha_catalogue.jsonl"
    _ALPHAS_DIR  = "alphas"

    def __init__(self, root: str = "data/alpha_memory", config: Optional[Dict] = None, **kwargs) -> None:
        if config and isinstance(config, dict):
            root = config.get("ALPHA_MEMORY_ROOT", root)

        self._root    = Path(root)
        self._alphas  = self._root / self._ALPHAS_DIR
        self._cat     = self._root / self._CATALOGUE
        self._index   = AlphaMemoryIndex()
        self._lock    = threading.RLock()

        self._root.mkdir(parents=True, exist_ok=True)
        self._alphas.mkdir(parents=True, exist_ok=True)

        self._rebuild_index()

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def record(self, rec: AlphaRecord) -> AlphaRecord:
        """Persist a new or updated AlphaRecord. Returns the written record."""
        with self._lock:
            now = _NOW()
            if not rec.created_at:
                rec.created_at = now
            rec.updated_at = now

            self._write_alpha_file(rec)
            self._append_catalogue(rec)
            self._index.add(rec)
            return rec

    def record_from_dict(self, d: Dict) -> AlphaRecord:
        """Convenience: record from a plain dict (e.g. from evolution engine)."""
        return self.record(AlphaRecord.from_dict(d))

    def update_live_stats(
        self,
        strategy_id:     str,
        live_sharpe:     Optional[float] = None,
        live_drawdown:   Optional[float] = None,
        live_trade_count: Optional[int]  = None,
        shadow_passed:   Optional[bool]  = None,
        promoted:        Optional[bool]  = None,
        status:          Optional[str]   = None,
    ) -> Optional[AlphaRecord]:
        """Update in-place live performance fields for an existing alpha."""
        with self._lock:
            rec = self._index.get(strategy_id)
            if rec is None:
                return None
            if live_sharpe     is not None: rec.live_sharpe      = live_sharpe
            if live_drawdown   is not None: rec.live_drawdown     = live_drawdown
            if live_trade_count is not None: rec.live_trade_count = live_trade_count
            if shadow_passed   is not None: rec.shadow_passed     = shadow_passed
            if promoted        is not None: rec.promoted_to_live  = promoted
            if status          is not None: rec.status            = status
            return self.record(rec)

    def retire(self, strategy_id: str, reason: str = "") -> Optional[AlphaRecord]:
        """Mark an alpha as retired."""
        with self._lock:
            rec = self._index.get(strategy_id)
            if rec is None:
                return None
            rec.status      = "retired"
            rec.retired_at  = _NOW()
            rec.retire_reason = reason
            return self.record(rec)

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get(self, strategy_id: str) -> Optional[AlphaRecord]:
        return self._index.get(strategy_id)

    def top_alphas(self, regime: Optional[str] = None, n: int = 10) -> List[AlphaRecord]:
        return self._index.top_n(n=n, regime=regime)

    def query_by_regime(self, regime: str) -> List[AlphaRecord]:
        return self._index.by_regime(regime)

    def query_by_family(self, family: str) -> List[AlphaRecord]:
        return self._index.by_family(family)

    def query_by_status(self, status: str) -> List[AlphaRecord]:
        """status: discovered | shadow | live | retired"""
        return self._index.by_status(status)

    def all_alphas(self) -> List[AlphaRecord]:
        return [self._index.get(i) for i in self._index.all_ids() if self._index.get(i)]

    def stats_summary(self) -> Dict[str, Any]:
        """Return aggregate statistics across the entire alpha library."""
        all_recs = self.all_alphas()
        if not all_recs:
            return {"total": 0}
        live    = [r for r in all_recs if r.status == "live"]
        shadow  = [r for r in all_recs if r.status == "shadow"]
        retired = [r for r in all_recs if r.status == "retired"]
        ig      = [r for r in all_recs if r.is_institutional_grade()]
        sharpes = [r.sharpe for r in all_recs if r.sharpe > 0]
        return {
            "total":              len(all_recs),
            "live":               len(live),
            "shadow":             len(shadow),
            "retired":            len(retired),
            "institutional_grade": len(ig),
            "avg_sharpe":         round(sum(sharpes) / len(sharpes), 4) if sharpes else 0.0,
            "best_sharpe":        round(max(sharpes), 4) if sharpes else 0.0,
            "families":           list({r.family for r in all_recs}),
            "regimes_covered":    list({r.regime for r in all_recs}),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_alpha_file(self, rec: AlphaRecord) -> None:
        path = self._alphas / f"{rec.strategy_id}.json"
        tmp  = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)   # atomic on POSIX

    def _append_catalogue(self, rec: AlphaRecord) -> None:
        line = json.dumps({
            "strategy_id": rec.strategy_id,
            "family":      rec.family,
            "regime":      rec.regime,
            "status":      rec.status,
            "sharpe":      rec.sharpe,
            "drawdown":    rec.drawdown,
            "score":       rec.composite_score(),
            "updated_at":  rec.updated_at,
        })
        with open(self._cat, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _rebuild_index(self) -> None:
        """Load all individual alpha files into the in-memory index."""
        if not self._alphas.exists():
            return
        for path in sorted(self._alphas.glob("*.json")):
            try:
                d   = json.loads(path.read_text(encoding="utf-8"))
                rec = AlphaRecord.from_dict(d)
                self._index.add(rec)
            except Exception:
                pass    # corrupt file — skip silently
