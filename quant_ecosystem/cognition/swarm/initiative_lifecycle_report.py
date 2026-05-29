from dataclasses import dataclass


@dataclass(frozen=True)
class InitiativeLifecycleReport:
    total_records: int
    active_records: int