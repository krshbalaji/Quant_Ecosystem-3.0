"""
quant_ecosystem/synthetic_market/synthetic_market_engine.py
============================================================
Synthetic Market Engine — Quant Ecosystem 3.0

Generates realistic artificial OHLCV price series by composing:
  • A RegimeSchedule      → drift/vol/autocorr parameters per bar
  • GBM with autocorrelation → log-return process
  • Intra-bar OHLC construction → realistic candle shapes
  • Shock event injection → discrete structural breaks
  • Volume simulation     → regime-aware volume with spikes

The output is a ``List[Dict]`` of OHLCV candles in the exact format
expected by ``BacktestEngine._coerce_data()``:

    {
        "open":   float,
        "high":   float,
        "low":    float,
        "close":  float,
        "volume": int,
        "ts":     str,         # ISO date string, e.g. "2024-01-02"
        "regime": str,         # regime name for this bar (metadata)
        "bar_idx": int,        # 0-based bar index
    }

Design
------
The return process per bar is:

    r_t = μ_regime + ρ × r_{t-1} + σ_regime × ε_t

where:
    μ_regime    = regime drift_daily
    ρ           = regime autocorr (AR(1) coefficient)
    σ_regime    = regime vol_daily
    ε_t         ~ N(0,1) with fat-tail draws mixed in

Intra-bar structure:
    open  = prior_close × (1 + gap_fraction)
    range = close × wick_ratio × |z|         (z ~ N(0,1))
    high  = max(open, close) + range/2
    low   = min(open, close) - range/2
    (then high ≥ open ≥ close ≥ low enforced)
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from quant_ecosystem.synthetic_market.regime_generator import (
    Regime,
    RegimeParams,
    RegimeSchedule,
    RegimeSegment,
    RegimeGenerator,
    REGIME_PARAMS,
)
from quant_ecosystem.synthetic_market.shock_events import (
    ShockEvent,
    ShockEventInjector,
)


# ---------------------------------------------------------------------------
# Candle builder
# ---------------------------------------------------------------------------

def _build_candle(
    prior_close:  float,
    ret:          float,
    params:       RegimeParams,
    rng:          random.Random,
    bar_idx:      int,
    date_str:     str,
    base_volume:  float = 100_000.0,
) -> Dict[str, Any]:
    """Construct one OHLCV candle dict from a return and regime parameters."""

    close = max(0.001, prior_close * (1.0 + ret))

    # Intra-bar gap fraction (small overnight/session gap in open)
    gap_frac = rng.gauss(0, params.vol_daily * 0.3)
    open_    = max(0.001, prior_close * (1.0 + gap_frac))

    # Range (high-low) driven by wick_ratio and intra-bar volatility
    intra_vol = params.wick_ratio * close * abs(rng.gauss(0.5, 0.3))
    intra_vol = max(intra_vol, close * 0.001)    # minimum 0.1% range

    # Body sits within range
    hi_raw = max(open_, close) + intra_vol * params.body_ratio
    lo_raw = min(open_, close) - intra_vol * params.body_ratio
    high   = max(hi_raw, open_, close)
    low    = max(0.001, min(lo_raw, open_, close))

    # Volume: log-normal around baseline, regime-scaled
    vol_base   = base_volume * params.volume_mult
    vol_scalar = math.exp(rng.gauss(0, 0.4))   # log-normal dispersion
    volume     = max(1, int(vol_base * vol_scalar))

    return {
        "open":    round(open_,  4),
        "high":    round(high,   4),
        "low":     round(low,    4),
        "close":   round(close,  4),
        "volume":  volume,
        "ts":      date_str,
        "regime":  params.regime.value,
        "bar_idx": bar_idx,
    }


# ---------------------------------------------------------------------------
# SyntheticSeries
# ---------------------------------------------------------------------------

@dataclass
class SyntheticSeries:
    """
    Result of one synthetic market generation run.

    Attributes
    ----------
    candles         OHLCV list ready for BacktestEngine.
    schedule        RegimeSchedule used to generate this series.
    shock_events    ShockEvents injected into the series.
    symbol          Synthetic instrument name.
    seed            RNG seed for reproducibility.
    metadata        Generation parameters and statistics.
    """

    candles:      List[Dict[str, Any]]
    schedule:     RegimeSchedule
    shock_events: List[ShockEvent]    = field(default_factory=list)
    symbol:       str                 = "SYNTH"
    seed:         Optional[int]       = None
    metadata:     Dict[str, Any]      = field(default_factory=dict)

    @property
    def n_bars(self) -> int:
        return len(self.candles)

    def close_series(self) -> List[float]:
        return [c["close"] for c in self.candles]

    def regime_at_bar(self, idx: int) -> str:
        if 0 <= idx < len(self.candles):
            return str(self.candles[idx].get("regime", "UNKNOWN"))
        return "UNKNOWN"

    def slice_by_regime(self, regime: Regime) -> List[Dict]:
        """Return only the candles belonging to one regime."""
        return [c for c in self.candles if c.get("regime") == regime.value]

    def summary(self) -> Dict[str, Any]:
        closes    = self.close_series()
        total_ret = (closes[-1] / closes[0] - 1.0) * 100.0 if closes else 0.0
        rets      = [(closes[i] - closes[i-1]) / closes[i-1]
                     for i in range(1, len(closes))]
        mean_r    = sum(rets) / len(rets) if rets else 0.0
        std_r     = math.sqrt(sum((r - mean_r)**2 for r in rets) / max(1, len(rets)-1)) if rets else 0.0
        sharpe    = mean_r / std_r * math.sqrt(252) if std_r > 0 else 0.0

        peak = closes[0]
        max_dd = 0.0
        for c in closes:
            peak = max(peak, c)
            if peak > 0:
                max_dd = max(max_dd, (peak - c) / peak * 100.0)

        return {
            "symbol":       self.symbol,
            "n_bars":       self.n_bars,
            "total_return": round(total_ret, 4),
            "ann_sharpe":   round(sharpe,    4),
            "max_dd_pct":   round(max_dd,    4),
            "shock_count":  len(self.shock_events),
            "regime_coverage": self.schedule.coverage(),
            "start_price":  round(closes[0],  4) if closes else 0.0,
            "end_price":    round(closes[-1],  4) if closes else 0.0,
        }


# ---------------------------------------------------------------------------
# SyntheticMarketEngine
# ---------------------------------------------------------------------------

class SyntheticMarketEngine:
    """
    Core engine for generating synthetic OHLCV market data.

    Usage
    -----
        engine = SyntheticMarketEngine(seed=42)

        # Generate 504 bars (2 years) with a random regime sequence
        series = engine.generate(n_bars=504)
        candles = series.candles  # → List[Dict], ready for BacktestEngine

        # Use a specific scenario
        regime_gen = RegimeGenerator()
        schedule   = regime_gen.generate_scenario("bear_market")
        series     = engine.generate_from_schedule(schedule, inject_shocks=True)

        # Stress test series with all event types
        series = engine.generate_stress(n_bars=252, regime=Regime.HIGH_VOL)

        # Regime sweep: one segment per regime
        multi = engine.generate_regime_sweep(bars_per_regime=100)
        # multi = {"TREND_UP": series, "TREND_DOWN": series, ...}
    """

    def __init__(
        self,
        seed:           Optional[int]  = None,
        initial_price:  float          = 1000.0,
        base_volume:    float          = 100_000.0,
        start_date:     str            = "2024-01-02",
        config:         Optional[Dict] = None,
        **kwargs,
    ) -> None:
        if config and isinstance(config, dict):
            seed          = config.get("SYNTH_SEED",           seed)
            initial_price = config.get("SYNTH_INITIAL_PRICE",  initial_price)
            base_volume   = config.get("SYNTH_BASE_VOLUME",    base_volume)

        self._seed          = seed
        self._initial_price = float(initial_price)
        self._base_volume   = float(base_volume)
        self._start_date    = start_date
        self._rng           = random.Random(seed)
        self._regime_gen    = RegimeGenerator(seed=seed)
        self._injector      = ShockEventInjector(seed=seed)

    # ------------------------------------------------------------------
    # Primary generation methods
    # ------------------------------------------------------------------

    def generate(
        self,
        n_bars:        int            = 504,
        inject_shocks: bool           = True,
        n_shocks:      int            = 5,
        seed:          Optional[int]  = None,
        symbol:        str            = "SYNTH",
    ) -> SyntheticSeries:
        """
        Generate a random regime sequence of n_bars with optional shocks.
        Equivalent to ``generate_from_schedule`` with a random schedule.
        """
        rng_seed = seed if seed is not None else self._rng.randint(0, 2**31)
        schedule = RegimeGenerator(seed=rng_seed).generate_random(
            total_bars = n_bars,
            seed       = rng_seed,
        )
        return self.generate_from_schedule(
            schedule       = schedule,
            inject_shocks  = inject_shocks,
            n_shocks       = n_shocks,
            seed           = rng_seed,
            symbol         = symbol,
        )

    def generate_from_schedule(
        self,
        schedule:      RegimeSchedule,
        inject_shocks: bool          = True,
        n_shocks:      int           = 5,
        initial_price: Optional[float] = None,
        seed:          Optional[int] = None,
        symbol:        str           = "SYNTH",
    ) -> SyntheticSeries:
        """
        Generate OHLCV candles driven by a RegimeSchedule.

        Each regime segment uses its own statistical parameters for the
        AR(1) return process.
        """
        rng_seed = seed if seed is not None else self._rng.randint(0, 2**31)
        rng      = random.Random(rng_seed)
        price0   = initial_price or self._initial_price

        # Expand schedule to per-bar list
        regime_at: List[RegimeSegment] = schedule.regime_at
        n_bars    = schedule.total_bars
        candles   = []
        price     = price0
        prev_ret  = 0.0     # AR(1) state

        date_cursor = self._date_gen(self._start_date)

        for bar_idx in range(n_bars):
            seg    = regime_at[bar_idx]
            params = seg.params
            date   = next(date_cursor)

            # AR(1) return with fat-tail mixing
            z = rng.gauss(0.0, 1.0)
            if rng.random() < params.fat_tail_prob:
                z *= params.fat_tail_mult    # fat-tail draw

            ret = (
                params.drift_daily
                + params.autocorr * prev_ret
                + params.vol_daily * z
            )
            # Clip extreme returns
            ret = max(-0.20, min(0.20, ret))

            candle  = _build_candle(
                prior_close = price,
                ret         = ret,
                params      = params,
                rng         = rng,
                bar_idx     = bar_idx,
                date_str    = date,
                base_volume = self._base_volume,
            )
            candles.append(candle)
            price    = candle["close"]
            prev_ret = ret

        # Inject shock events
        shock_events: List[ShockEvent] = []
        if inject_shocks and n_shocks > 0 and len(candles) >= 30:
            candles, shock_events = self._injector.inject_random(
                candles, n_events=n_shocks, seed=rng_seed + 1
            )

        return SyntheticSeries(
            candles      = candles,
            schedule     = schedule,
            shock_events = shock_events,
            symbol       = symbol,
            seed         = rng_seed,
            metadata     = {
                "generator":   "SyntheticMarketEngine",
                "n_bars":      n_bars,
                "initial_price": price0,
                "n_shocks":    len(shock_events),
                "schedule":    schedule.to_dict(),
                "created_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

    def generate_scenario(
        self,
        name:          str,
        inject_shocks: bool = True,
        n_shocks:      int  = 4,
        seed:          Optional[int] = None,
        symbol:        Optional[str] = None,
    ) -> SyntheticSeries:
        """Generate a named scenario (e.g. 'bear_market', 'covid_crash')."""
        schedule = self._regime_gen.generate_scenario(name)
        return self.generate_from_schedule(
            schedule       = schedule,
            inject_shocks  = inject_shocks,
            n_shocks       = n_shocks,
            seed           = seed,
            symbol         = symbol or f"SYNTH_{name.upper()}",
        )

    def generate_stress(
        self,
        regime:        Regime         = Regime.HIGH_VOL,
        n_bars:        int            = 252,
        inject_shocks: bool           = True,
        seed:          Optional[int]  = None,
    ) -> SyntheticSeries:
        """Single-regime stress test series."""
        schedule = self._regime_gen.generate_stress(regime=regime, n_bars=n_bars)
        return self.generate_from_schedule(
            schedule       = schedule,
            inject_shocks  = inject_shocks,
            n_shocks       = 3,
            seed           = seed,
            symbol         = f"SYNTH_STRESS_{regime.value}",
        )

    def generate_regime_sweep(
        self,
        bars_per_regime: int          = 100,
        inject_shocks:   bool         = False,
        seed:            Optional[int] = None,
    ) -> Dict[str, SyntheticSeries]:
        """
        Generate one SyntheticSeries per regime for cross-regime testing.

        Returns
        -------
        dict mapping regime name → SyntheticSeries
        """
        result: Dict[str, SyntheticSeries] = {}
        base_seed = seed if seed is not None else self._rng.randint(0, 2**31)
        for i, regime in enumerate(Regime):
            series = self.generate_stress(
                regime         = regime,
                n_bars         = bars_per_regime,
                inject_shocks  = inject_shocks,
                seed           = base_seed + i,
            )
            result[regime.value] = series
        return result

    def generate_multi_scenario(
        self,
        scenario_names: Optional[List[str]] = None,
        inject_shocks:  bool                = True,
        seed:           Optional[int]       = None,
    ) -> Dict[str, SyntheticSeries]:
        """
        Generate multiple named scenarios.

        Returns dict mapping scenario_name → SyntheticSeries.
        """
        names      = scenario_names or self._regime_gen.list_scenarios()
        base_seed  = seed if seed is not None else self._rng.randint(0, 2**31)
        return {
            name: self.generate_scenario(
                name          = name,
                inject_shocks = inject_shocks,
                seed          = base_seed + i,
            )
            for i, name in enumerate(names)
        }

    def inject_stress_events(self, series: SyntheticSeries) -> SyntheticSeries:
        """
        Post-inject the full stress event suite onto an existing SyntheticSeries.
        Returns a new SyntheticSeries (original unchanged).
        """
        candles, events = self._injector.inject_stress_suite(series.candles)
        return SyntheticSeries(
            candles      = candles,
            schedule     = series.schedule,
            shock_events = series.shock_events + events,
            symbol       = series.symbol + "_STRESS",
            seed         = series.seed,
            metadata     = dict(series.metadata, stress_injected=True),
        )

    # ------------------------------------------------------------------
    # Utility: list available scenarios
    # ------------------------------------------------------------------

    def list_scenarios(self) -> List[str]:
        return self._regime_gen.list_scenarios()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _date_gen(start: str):
        """Yield trading date strings from start_date, skipping weekends."""
        try:
            import datetime
            parts  = [int(x) for x in start.split("-")]
            cursor = datetime.date(parts[0], parts[1], parts[2])
            while True:
                if cursor.weekday() < 5:   # Mon-Fri
                    yield cursor.isoformat()
                cursor += datetime.timedelta(days=1)
        except Exception:
            # Fallback: yield incrementing fake dates
            i = 0
            while True:
                yield f"bar_{i:05d}"
                i += 1
