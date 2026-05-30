from dataclasses import dataclass


@dataclass(frozen=True)
class RiskReport:
    highest_risk_category: str
    highest_risk_score: float