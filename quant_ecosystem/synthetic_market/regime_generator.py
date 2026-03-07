"""
quant_ecosystem/synthetic_market/regime_generator.py
=====================================================
Regime Generator — Quant Ecosystem 3.0

Defines five market regimes and generates scheduled sequences of them.

Regimes
-------
TREND_UP        Persistent upward drift, low mean-reversion, moderate vol
TREND_DOWN      Persistent downward drift, low mean-reversion, moderate vol
SIDEWAYS        Near-zero drift, high mean-reversion, low vol
HIGH_VOL        Any direction possible, elevated volatility, fat tails
LOW_VOL         Near-zero drift, very tight ranges, high serial correlation

Each regime is characterised by:
    drift           Daily return expectation (annualised / 252)
    vol             Daily volatility (annualised / sqrt(252))
    autocorr        Serial correlation of returns (-1…+1)
    mean_reversion  Strength of mean-reversion force (0…1)
    fat_tail_mult   Multiplier for tail draw probability
    spread_bps      Bid-ask spread in basis points (affects fill quality)
    volume_mult     Volume relative to baseline (1.0 = normal)

RegimeSchedule
--------------
An ordered list of (regime, n_bars) pairs that together form a full
synthetic time series spec.  The SyntheticMarketEngine consumes this.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Regime enum
# ---------------------------------------------------------------------------

class Regime(str, Enum):
    TREND_UP   = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    SIDEWAYS   = "SIDEWAYS"
    HIGH_VOL   = "HIGH_VOL"
    LOW_VOL    = "LOW_VOL"


# ---------------------------------------------------------------------------
# Regime parameters
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeParams:
    """Statistical properties for one market regime."""

    regime:           Regime

    # Return distribution
    drift_daily:      float      # expected daily return (e.g. 0.0008 = +0.08%/day)
    vol_daily:        float      # daily volatility (e.g. 0.012 = 1.2%/day)
    autocorr:         float      # [-1, +1] — momentum (+) or reversion (-)
    fat_tail_prob:    float      # probability of a tail draw on any bar (0–1)
    fat_tail_mult:    float      # size multiplier for tail draws (e.g. 3.0 = 3× normal move)

    # Microstructure
    spread_bps:       float      # typical bid-ask half-spread in bps
    volume_mult:      float      # volume relative to baseline

    # Intra-bar structure
    wick_ratio:       float      # avg high-low / close (0–1)
    body_ratio:       float      # avg |open-close| / high-low (0–1)

    def daily_std(self) -> float:
        return self.vol_daily

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "regime":        self.regime.value,
            "drift_daily":   self.drift_daily,
            "vol_daily":     self.vol_daily,
            "autocorr":      self.autocorr,
            "fat_tail_prob": self.fat_tail_prob,
            "fat_tail_mult": self.fat_tail_mult,
            "spread_bps":    self.spread_bps,
            "volume_mult":   self.volume_mult,
            "wick_ratio":    self.wick_ratio,
            "body_ratio":    self.body_ratio,
        }
        return d


# ---------------------------------------------------------------------------
# Calibrated regime parameter library
# ---------------------------------------------------------------------------
# Calibrated against approximate empirical equity market behaviour.

REGIME_PARAMS: Dict[Regime, RegimeParams] = {

    Regime.TREND_UP: RegimeParams(
        regime         = Regime.TREND_UP,
        drift_daily    = +0.0010,    # +0.10%/day ≈ +28% annualised
        vol_daily      = 0.0110,     # 1.1%/day  ≈ 17.5% annualised
        autocorr       = +0.12,      # mild positive autocorr (trend persistence)
        fat_tail_prob  = 0.03,
        fat_tail_mult  = 2.5,
        spread_bps     = 3.0,
        volume_mult    = 1.2,
        wick_ratio     = 0.010,
        body_ratio     = 0.60,
    ),

    Regime.TREND_DOWN: RegimeParams(
        regime         = Regime.TREND_DOWN,
        drift_daily    = -0.0012,    # -0.12%/day ≈ -26% annualised
        vol_daily      = 0.0145,     # 1.45%/day — bear markets are more volatile
        autocorr       = +0.10,
        fat_tail_prob  = 0.05,       # more frequent large down-days
        fat_tail_mult  = 3.0,
        spread_bps     = 6.0,        # wider spreads during sell-offs
        volume_mult    = 1.4,
        wick_ratio     = 0.016,
        body_ratio     = 0.55,
    ),

    Regime.SIDEWAYS: RegimeParams(
        regime         = Regime.SIDEWAYS,
        drift_daily    = 0.0000,
        vol_daily      = 0.0075,     # 0.75%/day ≈ 12% annualised
        autocorr       = -0.18,      # mean-reversion character
        fat_tail_prob  = 0.015,
        fat_tail_mult  = 2.0,
        spread_bps     = 4.0,
        volume_mult    = 0.8,
        wick_ratio     = 0.012,
        body_ratio     = 0.45,
    ),

    Regime.HIGH_VOL: RegimeParams(
        regime         = Regime.HIGH_VOL,
        drift_daily    = 0.0000,
        vol_daily      = 0.0250,     # 2.5%/day ≈ 40% annualised
        autocorr       = -0.05,
        fat_tail_prob  = 0.10,       # frequent tail events
        fat_tail_mult  = 4.0,
        spread_bps     = 12.0,       # wide spreads in high-vol environments
        volume_mult    = 1.8,
        wick_ratio     = 0.025,
        body_ratio     = 0.50,
    ),

    Regime.LOW_VOL: RegimeParams(
        regime         = Regime.LOW_VOL,
        drift_daily    = 0.0002,
        vol_daily      = 0.0040,     # 0.4%/day ≈ 6% annualised
        autocorr       = +0.25,      # high serial correlation (quiet trending)
        fat_tail_prob  = 0.005,
        fat_tail_mult  = 2.0,
        spread_bps     = 2.0,
        volume_mult    = 0.6,
        wick_ratio     = 0.006,
        body_ratio     = 0.70,
    ),
}


# ---------------------------------------------------------------------------
# RegimeSegment
# ---------------------------------------------------------------------------

@dataclass
class RegimeSegment:
    """One continuous block of a single regime in the schedule."""
    regime:     Regime
    n_bars:     int
    start_bar:  int           = 0   # filled in by RegimeSchedule.build()
    params:     RegimeParams  = field(default_factory=lambda: REGIME_PARAMS[Regime.SIDEWAYS])

    def __post_init__(self):
        self.params = REGIME_PARAMS[self.regime]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime":    self.regime.value,
            "n_bars":    self.n_bars,
            "start_bar": self.start_bar,
        }


# ---------------------------------------------------------------------------
# RegimeSchedule
# ---------------------------------------------------------------------------

@dataclass
class RegimeSchedule:
    """
    Ordered sequence of RegimeSegments forming a complete market scenario.

    Usage
    -----
        schedule = RegimeSchedule.from_list([
            (Regime.LOW_VOL,    60),
            (Regime.TREND_UP,   120),
            (Regime.HIGH_VOL,   40),
            (Regime.TREND_DOWN, 80),
            (Regime.SIDEWAYS,   100),
        ])
        # or use the generator:
        schedule = RegimeGenerator().generate_random(total_bars=504)
    """

    segments: List[RegimeSegment] = field(default_factory=list)

    @classmethod
    def from_list(cls, pairs: List[Tuple[Regime, int]]) -> "RegimeSchedule":
        segs = []
        cursor = 0
        for regime, n in pairs:
            seg = RegimeSegment(regime=regime, n_bars=n, start_bar=cursor)
            segs.append(seg)
            cursor += n
        return cls(segments=segs)

    @property
    def total_bars(self) -> int:
        return sum(s.n_bars for s in self.segments)

    @property
    def regime_at(self) -> List[RegimeSegment]:
        """Flat list: one entry per bar, pointing to its segment."""
        out = []
        for seg in self.segments:
            out.extend([seg] * seg.n_bars)
        return out

    def regime_sequence(self) -> List[Regime]:
        return [seg.regime for seg in self.segments]

    def coverage(self) -> Dict[str, float]:
        """Fraction of total bars in each regime."""
        total = max(self.total_bars, 1)
        counts: Dict[str, int] = {}
        for seg in self.segments:
            counts[seg.regime.value] = counts.get(seg.regime.value, 0) + seg.n_bars
        return {k: round(v / total, 4) for k, v in counts.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_bars": self.total_bars,
            "n_segments": len(self.segments),
            "coverage":   self.coverage(),
            "segments":   [s.to_dict() for s in self.segments],
        }


# ---------------------------------------------------------------------------
# RegimeGenerator
# ---------------------------------------------------------------------------

class RegimeGenerator:
    """
    Generates RegimeSchedules for synthetic market simulation.

    Three generation modes:

    generate_random(total_bars, seed)
        Randomly samples regime sequences weighted by typical market
        regime durations.

    generate_scenario(scenario_name)
        Pre-defined institutional scenario templates.

    generate_stress(regime, n_bars)
        Single-regime stress test (pure TREND_DOWN, pure HIGH_VOL, etc.)

    generate_regime_sweep(bars_per_regime)
        One segment of each regime in sequence — for full-coverage tests.
    """

    # Empirical weights: how likely each regime is to follow another
    _TRANSITION_WEIGHTS: Dict[Regime, Dict[Regime, float]] = {
        Regime.TREND_UP:   {Regime.TREND_UP: 0.50, Regime.SIDEWAYS: 0.20, Regime.HIGH_VOL: 0.15, Regime.LOW_VOL: 0.10, Regime.TREND_DOWN: 0.05},
        Regime.TREND_DOWN: {Regime.TREND_DOWN: 0.40, Regime.SIDEWAYS: 0.20, Regime.HIGH_VOL: 0.25, Regime.LOW_VOL: 0.05, Regime.TREND_UP: 0.10},
        Regime.SIDEWAYS:   {Regime.SIDEWAYS: 0.30, Regime.TREND_UP: 0.25, Regime.TREND_DOWN: 0.15, Regime.HIGH_VOL: 0.15, Regime.LOW_VOL: 0.15},
        Regime.HIGH_VOL:   {Regime.HIGH_VOL: 0.20, Regime.TREND_DOWN: 0.30, Regime.SIDEWAYS: 0.25, Regime.TREND_UP: 0.15, Regime.LOW_VOL: 0.10},
        Regime.LOW_VOL:    {Regime.LOW_VOL: 0.35, Regime.TREND_UP: 0.30, Regime.SIDEWAYS: 0.25, Regime.HIGH_VOL: 0.05, Regime.TREND_DOWN: 0.05},
    }

    # Typical regime duration in trading days (drawn from log-normal)
    _DURATION_PARAMS: Dict[Regime, Tuple[float, float]] = {
        Regime.TREND_UP:   (60, 30),    # mean=60, std=30 bars
        Regime.TREND_DOWN: (40, 20),
        Regime.SIDEWAYS:   (80, 40),
        Regime.HIGH_VOL:   (20, 10),
        Regime.LOW_VOL:    (100, 50),
    }

    # Pre-defined scenario templates
    _SCENARIOS: Dict[str, List[Tuple[Regime, int]]] = {
        "bull_market": [
            (Regime.LOW_VOL,    40),
            (Regime.TREND_UP,   120),
            (Regime.SIDEWAYS,   40),
            (Regime.TREND_UP,   100),
            (Regime.HIGH_VOL,   20),
            (Regime.TREND_UP,   80),
        ],
        "bear_market": [
            (Regime.TREND_DOWN, 80),
            (Regime.HIGH_VOL,   30),
            (Regime.TREND_DOWN, 60),
            (Regime.SIDEWAYS,   40),
            (Regime.HIGH_VOL,   20),
            (Regime.TREND_DOWN, 40),
        ],
        "crypto_2021": [
            (Regime.TREND_UP,   60),
            (Regime.HIGH_VOL,   20),
            (Regime.TREND_UP,   80),
            (Regime.HIGH_VOL,   40),
            (Regime.TREND_DOWN, 100),
            (Regime.SIDEWAYS,   60),
        ],
        "covid_crash": [
            (Regime.LOW_VOL,    60),
            (Regime.HIGH_VOL,   5),
            (Regime.TREND_DOWN, 25),
            (Regime.HIGH_VOL,   15),
            (Regime.TREND_UP,   80),
            (Regime.SIDEWAYS,   115),
        ],
        "choppy_year": [
            (Regime.SIDEWAYS, 60),
            (Regime.HIGH_VOL, 20),
            (Regime.SIDEWAYS, 60),
            (Regime.HIGH_VOL, 20),
            (Regime.SIDEWAYS, 80),
            (Regime.HIGH_VOL, 12),
        ],
        "full_cycle": [
            (Regime.LOW_VOL,    30),
            (Regime.TREND_UP,   100),
            (Regime.HIGH_VOL,   20),
            (Regime.TREND_DOWN, 80),
            (Regime.SIDEWAYS,   60),
            (Regime.TREND_UP,   60),
        ],
    }

    def __init__(
        self,
        seed:              Optional[int] = None,
        min_segment_bars:  int           = 15,
        config:            Optional[Dict] = None,
        **kwargs,
    ) -> None:
        self._rng             = random.Random(seed)
        self._min_bars        = max(5, min_segment_bars)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_random(
        self,
        total_bars: int = 504,
        seed:       Optional[int] = None,
    ) -> RegimeSchedule:
        """
        Generate a random realistic regime sequence via Markov transitions.
        Approximately matches historical equity market regime statistics.
        """
        rng = random.Random(seed) if seed is not None else self._rng
        pairs: List[Tuple[Regime, int]] = []
        remaining = total_bars
        current = rng.choice(list(Regime))

        while remaining > self._min_bars:
            # Duration: sample from truncated normal
            mean_dur, std_dur = self._DURATION_PARAMS[current]
            dur = max(self._min_bars, int(rng.gauss(mean_dur, std_dur)))
            dur = min(dur, remaining)
            pairs.append((current, dur))
            remaining -= dur
            if remaining <= 0:
                break
            # Transition
            current = self._markov_step(current, rng)

        return RegimeSchedule.from_list(pairs)

    def generate_scenario(self, name: str) -> RegimeSchedule:
        """Return a pre-defined institutional scenario schedule."""
        pairs = self._SCENARIOS.get(name)
        if pairs is None:
            raise ValueError(
                f"Unknown scenario {name!r}. Available: {list(self._SCENARIOS)}"
            )
        return RegimeSchedule.from_list(pairs)

    def generate_stress(
        self,
        regime:  Regime = Regime.HIGH_VOL,
        n_bars:  int    = 252,
    ) -> RegimeSchedule:
        """Single-regime stress test — all bars in one regime."""
        return RegimeSchedule.from_list([(regime, n_bars)])

    def generate_regime_sweep(
        self,
        bars_per_regime: int = 100,
    ) -> RegimeSchedule:
        """
        One segment of each regime in sequence.
        Guarantees every strategy is tested against all five regimes.
        """
        pairs = [(r, bars_per_regime) for r in Regime]
        return RegimeSchedule.from_list(pairs)

    def generate_multi_scenario(
        self,
        scenario_names: Optional[List[str]] = None,
        bars_per_regime: int = 80,
    ) -> Dict[str, RegimeSchedule]:
        """
        Generate a dict of named scenarios for cross-scenario testing.
        If no names supplied, returns all standard scenarios.
        """
        names = scenario_names or list(self._SCENARIOS.keys())
        return {name: self.generate_scenario(name) for name in names}

    def list_scenarios(self) -> List[str]:
        return list(self._SCENARIOS.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _markov_step(self, current: Regime, rng: random.Random) -> Regime:
        weights = self._TRANSITION_WEIGHTS[current]
        regimes = list(weights.keys())
        probs   = [weights[r] for r in regimes]
        total   = sum(probs)
        r_val   = rng.random() * total
        cumul   = 0.0
        for reg, prob in zip(regimes, probs):
            cumul += prob
            if r_val <= cumul:
                return reg
        return regimes[-1]
