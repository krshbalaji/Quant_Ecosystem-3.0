from __future__ import annotations

from typing import List

from quant_ecosystem.core.strategy_registry import StrategyRegistry
from quant_ecosystem.strategies.trend.ema_trend import EMATrendStrategy
from quant_ecosystem.strategies.trend.breakout_trend import BreakoutTrendStrategy
from quant_ecosystem.strategies.trend.donchian_trend import DonchianTrendStrategy
from quant_ecosystem.strategies.mean_reversion.rsi_reversion import RSIMeanReversionStrategy
from quant_ecosystem.strategies.mean_reversion.bollinger_reversion import BollingerReversionStrategy
from quant_ecosystem.strategies.mean_reversion.vwap_reversion import VWAPReversionStrategy
from quant_ecosystem.strategies.momentum.cross_section_momentum import CrossSectionMomentumStrategy
from quant_ecosystem.strategies.momentum.time_series_momentum import TimeSeriesMomentumStrategy
from quant_ecosystem.strategies.volatility.atr_breakout import ATRBreakoutStrategy
from quant_ecosystem.strategies.volatility.volatility_expansion import VolatilityExpansionStrategy
from quant_ecosystem.strategies.microstructure.liquidity_imbalance import LiquidityImbalanceStrategy
from quant_ecosystem.strategies.microstructure.volume_spike import VolumeSpikeStrategy


class StrategyUniverse:
    """
    Institutional strategy universe manager.
    Responsible for instantiating and registering all core strategies.
    """

    def __init__(self, **kwargs) -> None:
        self._strategies = self._build_universe()

    def _build_universe(self):
        return [
            EMATrendStrategy(),
            BreakoutTrendStrategy(),
            DonchianTrendStrategy(),
            RSIMeanReversionStrategy(),
            BollingerReversionStrategy(),
            VWAPReversionStrategy(),
            CrossSectionMomentumStrategy(),
            TimeSeriesMomentumStrategy(),
            ATRBreakoutStrategy(),
            VolatilityExpansionStrategy(),
            LiquidityImbalanceStrategy(),
            VolumeSpikeStrategy(),
        ]

    @property
    def strategies(self) -> List[object]:
        return list(self._strategies)

    def load_strategies(self, registry: StrategyRegistry) -> None:
        """
        Register all institutional strategies into the shared registry.
        """
        for strategy in self._strategies:
            registry.register(strategy)

