from dataclasses import dataclass


@dataclass(frozen=True)
class FederationHealthReport:
    total_capabilities: int
    healthy_capabilities: int