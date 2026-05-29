from dataclasses import dataclass


@dataclass(frozen=True)
class FederationHandoff:
    action_id: str
    target_system: str
    accepted: bool