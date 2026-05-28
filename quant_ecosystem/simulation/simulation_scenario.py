from dataclasses import dataclass


@dataclass
class SimulationScenario:

    volatility: float

    liquidity: float

    broker_health: float

    stress_level: float