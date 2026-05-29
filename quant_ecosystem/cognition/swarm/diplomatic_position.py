from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DiplomaticPosition:
    organism_id: str
    objectives: Dict[str, float] = field(default_factory=dict)
    negotiation_flexibility: float = 0.5

    def strategic_weight(
        self,
        domain: str,
    ) -> float:

        return self.objectives.get(domain, 0.0)