"""
quant_ecosystem/synthetic_market
=================================
Synthetic Market Simulator — Quant Ecosystem 3.0

Public surface
--------------
SyntheticMarketEngine       Core OHLCV price series generator
RegimeGenerator             Regime schedule builder (5 regimes)
Regime                      Enum: TREND_UP | TREND_DOWN | SIDEWAYS | HIGH_VOL | LOW_VOL
RegimeSchedule              Ordered sequence of RegimeSegments
RegimeParams                Statistical properties per regime
ShockEventInjector          Injects flash_crash / liquidity_drop / gap_up / gap_down etc.
ShockEvent                  Shock descriptor (type, bar_index, magnitude, …)
ShockType                   Enum of all shock event types
SyntheticBacktester         Strategy robustness evaluator (StrategyLab / GenomeEvaluator hook)
RobustnessResult            Composite robustness result with per-regime breakdown
RegimeResult                Single-regime backtest metrics
SyntheticSeries             Generated OHLCV candle series with metadata
"""

from .regime_generator import (
    Regime,
    RegimeParams,
    RegimeSchedule,
    RegimeSegment,
    RegimeGenerator,
    REGIME_PARAMS,
)
from .shock_events import (
    ShockType,
    ShockEvent,
    ShockEventInjector,
)
from .synthetic_market_engine import (
    SyntheticMarketEngine,
    SyntheticSeries,
)
from .synthetic_backtester import (
    SyntheticBacktester,
    RobustnessResult,
    RegimeResult,
)

__all__ = [
    # Regime system
    "Regime",
    "RegimeParams",
    "RegimeSchedule",
    "RegimeSegment",
    "RegimeGenerator",
    "REGIME_PARAMS",
    # Shock events
    "ShockType",
    "ShockEvent",
    "ShockEventInjector",
    # Price generation
    "SyntheticMarketEngine",
    "SyntheticSeries",
    # Backtesting & robustness
    "SyntheticBacktester",
    "RobustnessResult",
    "RegimeResult",
]
