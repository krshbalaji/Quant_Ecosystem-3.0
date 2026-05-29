from dataclasses import dataclass


@dataclass(frozen=True)
class CouncilMember:
    organism_id: str
    voting_weight: float = 1.0