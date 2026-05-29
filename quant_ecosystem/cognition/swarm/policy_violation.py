from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyViolation:
    policy_id: str
    reason: str