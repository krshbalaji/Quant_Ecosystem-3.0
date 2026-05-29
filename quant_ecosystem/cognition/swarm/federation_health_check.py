from dataclasses import dataclass


@dataclass(frozen=True)
class FederationHealthCheck:
    healthy: bool
    component_count: int