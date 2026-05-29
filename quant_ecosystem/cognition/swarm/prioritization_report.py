from dataclasses import dataclass
from typing import List

from .prioritized_objective import (
    PrioritizedObjective,
)


@dataclass(frozen=True)
class PrioritizationReport:
    objective_count: int
    objectives: List[PrioritizedObjective]