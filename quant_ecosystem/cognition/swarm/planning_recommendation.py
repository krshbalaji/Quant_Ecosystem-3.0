from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningRecommendation:
    recommendation_id: str
    description: str