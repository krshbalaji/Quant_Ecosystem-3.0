from dataclasses import dataclass


@dataclass
class RegimeSnapshot:

    volatility: float

    liquidity: float

    trend_strength: float

    detected_regime: str