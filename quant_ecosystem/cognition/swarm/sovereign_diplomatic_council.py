from typing import Dict, List

from .diplomatic_treaty import DiplomaticTreaty
from .federation_conflict_resolver import (
    FederationConflictResolver,
)
from .diplomatic_position import DiplomaticPosition


class SovereignDiplomaticCouncil:

    def __init__(self):
        self.treaties: List[DiplomaticTreaty] = []
        self.resolver = FederationConflictResolver()

    def register_treaty(
        self,
        treaty: DiplomaticTreaty,
    ) -> None:

        self.treaties.append(treaty)

    def evaluate_interaction(
        self,
        left: DiplomaticPosition,
        right: DiplomaticPosition,
        domain: str,
    ) -> Dict:

        resolution = self.resolver.resolve(
            left,
            right,
            domain,
        )

        treaty_support = any(
            treaty.active
            and treaty.allows_domain(domain)
            and left.organism_id in treaty.participating_organisms
            and right.organism_id in treaty.participating_organisms
            for treaty in self.treaties
        )

        resolution["treaty_supported"] = treaty_support

        return resolution