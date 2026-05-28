from dataclasses import dataclass


@dataclass
class RealitySnapshot:

    broker_health: float

    liquidity: float

    volatility: float

    anomaly_score: float