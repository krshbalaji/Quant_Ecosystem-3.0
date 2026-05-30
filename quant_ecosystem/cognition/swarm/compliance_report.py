from dataclasses import dataclass


@dataclass(frozen=True)
class ComplianceReport:
    violation_count: int
    highest_severity: float