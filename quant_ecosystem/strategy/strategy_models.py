from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class StrategyState(Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"


class StrategyHealth(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass
class StrategyDefinition:
    strategy_id: str
    name: str

    state: StrategyState = StrategyState.ENABLED
    health: StrategyHealth = StrategyHealth.HEALTHY

    priority: int = 100
    capital_weight: float = 1.0

    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def is_active(self):
        return (
            self.state == StrategyState.ENABLED
            and self.health != StrategyHealth.FAILED
        )