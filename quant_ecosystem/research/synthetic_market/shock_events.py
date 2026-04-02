"""
quant_ecosystem/synthetic_market/shock_events.py
=================================================
Shock Events — Quant Ecosystem 3.0

Injects realistic market shock events into a candle series.

Events
------
flash_crash         Sudden multi-bar drop followed by partial recovery.
                    Mimics: 2010 Flash Crash, circuit-breaker episodes.

liquidity_drop      Bid-ask spreads widen, volume collapses, wicks explode.
                    Mimics: illiquid hours, thin order-books, auction opens.

gap_up              Overnight or intra-session gap upward (open >> prior close).
                    Mimics: earnings beats, geopolitical shock, index inclusion.

gap_down            Overnight or intra-session gap downward (open << prior close).
                    Mimics: earnings misses, credit events, surprise rate hikes.

spike_reversal      A single large move immediately mean-reverted.
                    Mimics: fat-finger trades, erroneous prints.

volatility_cluster  Sustained elevated volatility with autocorrelation of shocks.
                    Mimics: VIX regime transitions, FOMC, macro event windows.

ShockEvent
----------
Descriptor carrying the event type, bar index, and parametric spec.
All injection methods accept and return ``List[Dict]`` OHLCV candles.

ShockEventInjector
------------------
Primary interface.  Composes multiple events onto a candle series.
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class ShockType(str, Enum):
    FLASH_CRASH        = "flash_crash"
    LIQUIDITY_DROP     = "liquidity_drop"
    GAP_UP             = "gap_up"
    GAP_DOWN           = "gap_down"
    SPIKE_REVERSAL     = "spike_reversal"
    VOLATILITY_CLUSTER = "volatility_cluster"


# ---------------------------------------------------------------------------
# ShockEvent descriptor
# ---------------------------------------------------------------------------

@dataclass
class ShockEvent:
    """
    Description of one shock event to be injected into a candle series.

    Attributes
    ----------
    shock_type      The type of shock.
    bar_index       Bar at which the shock begins (0-based).
    magnitude       Primary shock magnitude:
                    • flash_crash:       fractional drop (e.g. 0.08 = -8%)
                    • gap_up / gap_down: fractional gap (e.g. 0.04 = +4%)
                    • spike_reversal:    intra-bar spike size fraction
                    • liquidity_drop:    spread multiplier (e.g. 5.0 = 5× normal)
                    • volatility_cluster: vol multiplier (e.g. 3.0 = 3× normal)
    duration_bars   How many bars the shock affects.
    recovery_frac   For flash_crash: fraction of the drop that recovers (0–1).
    spread_mult     Additional spread multiplier applied during shock.
    volume_mult     Volume multiplier applied during shock.
    label           Human-readable event description.
    """

    shock_type:      ShockType
    bar_index:       int
    magnitude:       float           = 0.05
    duration_bars:   int             = 3
    recovery_frac:   float           = 0.50
    spread_mult:     float           = 1.0
    volume_mult:     float           = 1.0
    label:           str             = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shock_type":    self.shock_type.value,
            "bar_index":     self.bar_index,
            "magnitude":     self.magnitude,
            "duration_bars": self.duration_bars,
            "recovery_frac": self.recovery_frac,
            "spread_mult":   self.spread_mult,
            "volume_mult":   self.volume_mult,
            "label":         self.label or self.shock_type.value,
        }


# ---------------------------------------------------------------------------
# ShockEventInjector
# ---------------------------------------------------------------------------

_CANDLE_FIELDS = ("open", "high", "low", "close", "volume")


class ShockEventInjector:
    """
    Injects shock events into a list of OHLCV candle dicts.

    Usage
    -----
        injector = ShockEventInjector(seed=42)

        # Inject a single flash crash at bar 100
        candles = injector.inject_flash_crash(candles, bar_index=100, magnitude=0.12)

        # Inject from a ShockEvent descriptor
        event = ShockEvent(ShockType.GAP_DOWN, bar_index=200, magnitude=0.05)
        candles = injector.inject(candles, event)

        # Inject a random set of events typical for a 1-year series
        candles, events = injector.inject_random(candles, n_events=6)

        # Check robustness: inject all event types once
        candles, events = injector.inject_stress_suite(candles)
    """

    def __init__(self, seed: Optional[int] = None, **kwargs) -> None:
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Primary dispatcher
    # ------------------------------------------------------------------

    def inject(self, candles: List[Dict], event: ShockEvent) -> List[Dict]:
        """Inject a single ShockEvent into the candle series."""
        if not candles or event.bar_index < 0 or event.bar_index >= len(candles):
            return candles

        dispatcher = {
            ShockType.FLASH_CRASH:        self._flash_crash,
            ShockType.LIQUIDITY_DROP:     self._liquidity_drop,
            ShockType.GAP_UP:             self._gap,
            ShockType.GAP_DOWN:           self._gap,
            ShockType.SPIKE_REVERSAL:     self._spike_reversal,
            ShockType.VOLATILITY_CLUSTER: self._volatility_cluster,
        }
        fn = dispatcher.get(event.shock_type)
        if fn is None:
            return candles
        return fn(candles, event)

    def inject_all(
        self,
        candles: List[Dict],
        events:  List[ShockEvent],
    ) -> List[Dict]:
        """Inject a list of ShockEvents in order."""
        result = [dict(c) for c in candles]
        for event in sorted(events, key=lambda e: e.bar_index):
            result = self.inject(result, event)
        return result

    # ------------------------------------------------------------------
    # Named injection convenience methods
    # ------------------------------------------------------------------

    def inject_flash_crash(
        self,
        candles:       List[Dict],
        bar_index:     int,
        magnitude:     float = 0.08,
        duration_bars: int   = 4,
        recovery_frac: float = 0.50,
    ) -> List[Dict]:
        """
        Sudden multi-bar decline followed by partial recovery.

        The crash is spread across `duration_bars` bars, then a recovery
        of `recovery_frac * magnitude` unfolds over the same number of bars.
        """
        event = ShockEvent(
            shock_type    = ShockType.FLASH_CRASH,
            bar_index     = bar_index,
            magnitude     = abs(magnitude),
            duration_bars = max(2, duration_bars),
            recovery_frac = max(0.0, min(1.0, recovery_frac)),
            spread_mult   = 3.0,
            volume_mult   = 2.5,
            label         = f"flash_crash({magnitude:.1%})",
        )
        return self.inject(candles, event)

    def inject_liquidity_drop(
        self,
        candles:       List[Dict],
        bar_index:     int,
        duration_bars: int   = 8,
        spread_mult:   float = 6.0,
        volume_mult:   float = 0.15,
    ) -> List[Dict]:
        """
        Sudden liquidity withdrawal: wicks explode, volume collapses.
        Price level unchanged but microstructure severely impaired.
        """
        event = ShockEvent(
            shock_type    = ShockType.LIQUIDITY_DROP,
            bar_index     = bar_index,
            magnitude     = 0.0,
            duration_bars = max(2, duration_bars),
            spread_mult   = max(1.0, spread_mult),
            volume_mult   = max(0.01, volume_mult),
            label         = f"liquidity_drop(spread×{spread_mult:.1f})",
        )
        return self.inject(candles, event)

    def inject_gap_up(
        self,
        candles:   List[Dict],
        bar_index: int,
        magnitude: float = 0.04,
    ) -> List[Dict]:
        """Gap up at open — open price jumps above prior close."""
        event = ShockEvent(
            shock_type    = ShockType.GAP_UP,
            bar_index     = bar_index,
            magnitude     = abs(magnitude),
            duration_bars = 1,
            volume_mult   = 1.8,
            label         = f"gap_up({magnitude:.1%})",
        )
        return self.inject(candles, event)

    def inject_gap_down(
        self,
        candles:   List[Dict],
        bar_index: int,
        magnitude: float = 0.04,
    ) -> List[Dict]:
        """Gap down at open — open price falls below prior close."""
        event = ShockEvent(
            shock_type    = ShockType.GAP_DOWN,
            bar_index     = bar_index,
            magnitude     = abs(magnitude),
            duration_bars = 1,
            volume_mult   = 2.0,
            label         = f"gap_down({magnitude:.1%})",
        )
        return self.inject(candles, event)

    def inject_spike_reversal(
        self,
        candles:   List[Dict],
        bar_index: int,
        magnitude: float = 0.06,
    ) -> List[Dict]:
        """Single-bar price spike immediately reversed on the next bar."""
        event = ShockEvent(
            shock_type    = ShockType.SPIKE_REVERSAL,
            bar_index     = bar_index,
            magnitude     = abs(magnitude),
            duration_bars = 2,
            volume_mult   = 3.0,
            label         = f"spike_reversal({magnitude:.1%})",
        )
        return self.inject(candles, event)

    # ------------------------------------------------------------------
    # Random and stress-suite injectors
    # ------------------------------------------------------------------

    def inject_random(
        self,
        candles:  List[Dict],
        n_events: int = 5,
        seed:     Optional[int] = None,
    ) -> Tuple[List[Dict], List[ShockEvent]]:
        """
        Inject N random shock events at statistically plausible positions.
        Returns (modified candles, list of ShockEvents injected).
        """
        rng    = random.Random(seed) if seed is not None else self._rng
        n      = len(candles)
        if n < 30:
            return candles, []

        events = self._sample_random_events(n, n_events, rng)
        return self.inject_all(candles, events), events

    def inject_stress_suite(
        self,
        candles: List[Dict],
        seed:    Optional[int] = None,
    ) -> Tuple[List[Dict], List[ShockEvent]]:
        """
        Inject one of each event type at evenly-spaced positions.
        Used for robustness testing: a strong strategy must survive all of these.
        """
        rng = random.Random(seed) if seed is not None else self._rng
        n   = len(candles)
        if n < 60:
            return candles, []

        step   = n // 7
        events = [
            ShockEvent(ShockType.FLASH_CRASH,        bar_index=step * 1, magnitude=0.07,  duration_bars=4, recovery_frac=0.50),
            ShockEvent(ShockType.GAP_DOWN,            bar_index=step * 2, magnitude=0.04),
            ShockEvent(ShockType.LIQUIDITY_DROP,      bar_index=step * 3, duration_bars=5, spread_mult=5.0, volume_mult=0.1),
            ShockEvent(ShockType.GAP_UP,              bar_index=step * 4, magnitude=0.04),
            ShockEvent(ShockType.SPIKE_REVERSAL,      bar_index=step * 5, magnitude=0.05),
            ShockEvent(ShockType.VOLATILITY_CLUSTER,  bar_index=step * 6, duration_bars=20, magnitude=3.0),
        ]
        return self.inject_all(candles, events), events

    # ------------------------------------------------------------------
    # Event implementations
    # ------------------------------------------------------------------

    def _flash_crash(self, candles: List[Dict], event: ShockEvent) -> List[Dict]:
        result = [dict(c) for c in candles]
        n      = len(result)
        start  = event.bar_index
        dur    = min(event.duration_bars, n - start)
        if dur < 1:
            return result

        total_drop     = event.magnitude
        per_bar_drop   = total_drop / dur
        recovery_total = total_drop * event.recovery_frac
        per_bar_rec    = recovery_total / dur

        price_mult = 1.0
        # Crash phase
        for i in range(dur):
            idx = start + i
            if idx >= n:
                break
            price_mult *= (1.0 - per_bar_drop)
            c = result[idx]
            wick_expand = 1.0 + 0.5 * per_bar_drop
            result[idx] = self._scale_candle(
                c, price_mult, wick_mult=wick_expand,
                volume_mult=event.volume_mult,
            )
        # Recovery phase (immediately after)
        rec_mult = price_mult
        for i in range(dur):
            idx = start + dur + i
            if idx >= n:
                break
            rec_mult *= (1.0 + per_bar_rec)
            c = result[idx]
            result[idx] = self._scale_candle(
                c, rec_mult / price_mult,   # relative to current level
                wick_mult=1.3,
                volume_mult=max(1.0, event.volume_mult * 0.7),
            )
        return result

    def _liquidity_drop(self, candles: List[Dict], event: ShockEvent) -> List[Dict]:
        """Widen high-low range and crush volume without moving close."""
        result = [dict(c) for c in candles]
        n      = len(result)
        start  = event.bar_index
        dur    = min(event.duration_bars, n - start)
        for i in range(dur):
            idx = start + i
            if idx >= n:
                break
            c      = dict(result[idx])
            close  = c["close"]
            spread = abs(c["high"] - c["low"]) * event.spread_mult
            c["high"]   = close + spread * 0.5
            c["low"]    = close - spread * 0.5
            c["volume"] = max(1, int(c.get("volume", 100000) * event.volume_mult))
            result[idx] = c
        return result

    def _gap(self, candles: List[Dict], event: ShockEvent) -> List[Dict]:
        """Apply a persistent gap from bar_index onward."""
        result = [dict(c) for c in candles]
        idx    = event.bar_index
        if idx <= 0 or idx >= len(result):
            return result

        direction = +1.0 if event.shock_type == ShockType.GAP_UP else -1.0
        gap_factor = 1.0 + direction * event.magnitude

        # Shift all bars from idx onward by gap_factor on open
        c = dict(result[idx])
        prior_close = result[idx - 1]["close"]
        new_open    = prior_close * gap_factor
        # Adjust the entire bar relative to the gap
        shift       = new_open - c["open"]
        c["open"]   = new_open
        c["high"]   = c["high"]  + shift
        c["low"]    = c["low"]   + shift
        c["close"]  = c["close"] + shift
        c["volume"] = int(c.get("volume", 100000) * event.volume_mult)
        result[idx] = c

        # Persist price shift on subsequent bars
        for i in range(idx + 1, len(result)):
            rc = dict(result[i])
            rc["open"]  += shift
            rc["high"]  += shift
            rc["low"]   += shift
            rc["close"] += shift
            result[i]    = rc

        return result

    def _spike_reversal(self, candles: List[Dict], event: ShockEvent) -> List[Dict]:
        """Single intra-bar spike with immediate reversal on the next bar."""
        result = [dict(c) for c in candles]
        idx    = event.bar_index
        n      = len(result)
        if idx < 0 or idx >= n:
            return result

        # The spike bar: create a large wick
        c           = dict(result[idx])
        direction   = 1.0 if self._rng.random() > 0.5 else -1.0
        spike_size  = c["close"] * event.magnitude
        if direction > 0:
            c["high"] = c["close"] + spike_size
        else:
            c["low"]  = c["close"] - spike_size
        c["volume"]   = int(c.get("volume", 100000) * event.volume_mult)
        result[idx]   = c

        # The reversal bar: close moves back
        if idx + 1 < n:
            rc = dict(result[idx + 1])
            rc["close"] = c["close"]  # reversal to original level
            result[idx + 1] = rc

        return result

    def _volatility_cluster(self, candles: List[Dict], event: ShockEvent) -> List[Dict]:
        """Multiply all bar ranges by the vol multiplier for duration_bars."""
        result = [dict(c) for c in candles]
        n      = len(result)
        start  = event.bar_index
        dur    = min(event.duration_bars, n - start)
        mult   = max(1.0, event.magnitude)     # magnitude = vol multiplier

        for i in range(dur):
            idx = start + i
            if idx >= n:
                break
            c      = dict(result[idx])
            close  = c["close"]
            centre = (c["high"] + c["low"]) / 2.0
            half   = (c["high"] - c["low"]) / 2.0 * mult
            c["high"]   = close + half
            c["low"]    = max(close - half, 0.001)
            c["open"]   = close + (c["open"] - close) * mult
            result[idx] = c
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scale_candle(
        c:           Dict,
        price_mult:  float,
        wick_mult:   float = 1.0,
        volume_mult: float = 1.0,
    ) -> Dict:
        """Scale all price fields of a candle dict."""
        out = dict(c)
        close = c["close"] * price_mult
        half_range = abs(c["high"] - c["low"]) / 2.0 * wick_mult
        out["close"]  = close
        out["open"]   = c["open"]   * price_mult
        out["high"]   = close + half_range
        out["low"]    = max(close - half_range, 0.001)
        out["volume"] = max(1, int(c.get("volume", 100000) * volume_mult))
        return out

    def _sample_random_events(
        self,
        n_bars:   int,
        n_events: int,
        rng:      random.Random,
    ) -> List[ShockEvent]:
        """Sample N plausible random shock events within [20, n_bars-20]."""
        margin   = max(10, n_bars // 20)
        pool     = list(range(margin, n_bars - margin))
        if len(pool) < n_events:
            return []
        positions = sorted(rng.sample(pool, min(n_events, len(pool))))
        events    = []
        shock_types = list(ShockType)
        for pos in positions:
            stype = rng.choice(shock_types)
            if stype == ShockType.FLASH_CRASH:
                e = ShockEvent(stype, bar_index=pos, magnitude=rng.uniform(0.04, 0.14),
                               duration_bars=rng.randint(3, 6), recovery_frac=rng.uniform(0.3, 0.8),
                               volume_mult=rng.uniform(1.5, 3.0))
            elif stype == ShockType.LIQUIDITY_DROP:
                e = ShockEvent(stype, bar_index=pos, duration_bars=rng.randint(3, 10),
                               spread_mult=rng.uniform(3.0, 8.0), volume_mult=rng.uniform(0.05, 0.2))
            elif stype in (ShockType.GAP_UP, ShockType.GAP_DOWN):
                e = ShockEvent(stype, bar_index=pos, magnitude=rng.uniform(0.02, 0.07),
                               volume_mult=rng.uniform(1.5, 2.5))
            elif stype == ShockType.SPIKE_REVERSAL:
                e = ShockEvent(stype, bar_index=pos, magnitude=rng.uniform(0.03, 0.09),
                               volume_mult=rng.uniform(2.0, 4.0))
            else:  # VOLATILITY_CLUSTER
                e = ShockEvent(stype, bar_index=pos, magnitude=rng.uniform(2.0, 5.0),
                               duration_bars=rng.randint(10, 30))
            events.append(e)
        return events
