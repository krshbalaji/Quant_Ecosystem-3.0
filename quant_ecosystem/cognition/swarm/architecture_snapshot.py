from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureSnapshot:
    snapshot_id: str
    component_count: int