from dataclasses import dataclass


@dataclass(frozen=True)
class RoadmapMilestone:
    milestone_id: str
    description: str