from dataclasses import dataclass


@dataclass(frozen=True)
class ImprovementRecommendation:
    recommended_category: str
    improvement_score: float