from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceDecision:
    initiative_id: str
    approved: bool