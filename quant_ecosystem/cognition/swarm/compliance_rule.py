from dataclasses import dataclass


@dataclass(frozen=True)
class ComplianceRule:
    rule_id: str
    category: str