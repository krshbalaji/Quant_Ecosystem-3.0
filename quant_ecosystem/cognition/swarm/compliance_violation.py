from dataclasses import dataclass


@dataclass(frozen=True)
class ComplianceViolation:
    rule_id: str
    severity: float