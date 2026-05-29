from dataclasses import dataclass


@dataclass(frozen=True)
class FederationPolicy:
    policy_id: str
    domain: str
    minimum_confidence: float = 0.60
    active: bool = True