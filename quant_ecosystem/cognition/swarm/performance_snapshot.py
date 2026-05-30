from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceSnapshot:
    execution_id: str
    successful: bool