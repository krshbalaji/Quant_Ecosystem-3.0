from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceEnforcementRecord:
    policy_id: str
    outcome: str
    compliant: bool