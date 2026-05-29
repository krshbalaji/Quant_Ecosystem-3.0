from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceReviewRecord:
    initiative_id: str
    reviewed: bool