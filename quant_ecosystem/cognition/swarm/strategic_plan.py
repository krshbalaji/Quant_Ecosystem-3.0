from dataclasses import dataclass
from typing import List

from .strategic_objective import (
    StrategicObjective,
)


@dataclass(frozen=True)
class StrategicPlan:
    objective_count: int
    objectives: List[StrategicObjective]