from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class DiplomaticTreaty:
    treaty_id: str
    participating_organisms: List[str]
    permitted_domains: List[str] = field(default_factory=list)
    strategic_priority: int = 1
    active: bool = True

    def allows_domain(
        self,
        domain: str,
    ) -> bool:

        return domain in self.permitted_domains