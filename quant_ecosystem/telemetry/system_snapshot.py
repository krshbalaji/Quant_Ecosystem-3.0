from dataclasses import dataclass


@dataclass
class SystemSnapshot:

    execution_latency_ms: float

    broker_health_score: float

    retry_pressure: float

    queue_depth: int

    capital_utilization: float

    risk_utilization: float

    regime_state: str

    timestamp: str