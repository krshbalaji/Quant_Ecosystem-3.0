from dataclasses import dataclass


@dataclass(frozen=True)
class RiskIndicator:
    category_name: str
    risk_score: float