from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationContract:
    target_system: str
    enabled: bool = True