from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceResolution:
    resolution_id: str
    outcome: str
    confidence: float
    participant_count: int