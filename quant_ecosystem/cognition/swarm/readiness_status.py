from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessStatus:
    capability_id: str
    ready: bool