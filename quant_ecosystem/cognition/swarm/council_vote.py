from dataclasses import dataclass


@dataclass(frozen=True)
class CouncilVote:
    organism_id: str
    decision: str