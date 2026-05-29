from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDriftRecord:
    previous_count: int
    current_count: int