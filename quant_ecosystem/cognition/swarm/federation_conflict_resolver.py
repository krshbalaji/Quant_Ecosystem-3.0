from typing import Dict

from .diplomatic_alignment_engine import (
    DiplomaticAlignmentEngine,
)
from .diplomatic_position import DiplomaticPosition


class FederationConflictResolver:

    def __init__(self):
        self.alignment_engine = DiplomaticAlignmentEngine()

    def resolve(
        self,
        left: DiplomaticPosition,
        right: DiplomaticPosition,
        domain: str,
    ) -> Dict:

        alignment = self.alignment_engine.evaluate_alignment(
            left,
            right,
            domain,
        )

        if alignment >= 0.75:
            outcome = "cooperate"
        elif alignment >= 0.4:
            outcome = "negotiate"
        else:
            outcome = "contain"

        return {
            "domain": domain,
            "alignment": alignment,
            "resolution": outcome,
        }