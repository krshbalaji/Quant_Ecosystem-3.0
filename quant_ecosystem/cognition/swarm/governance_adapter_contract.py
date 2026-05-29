from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceAdapterContract:
    adapter_id: str
    subsystem_name: str
    enabled: bool = True