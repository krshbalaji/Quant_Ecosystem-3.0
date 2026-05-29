from dataclasses import dataclass
from typing import List

from .roadmap_step import RoadmapStep


@dataclass(frozen=True)
class StrategicRoadmap:
    roadmap_steps: List[RoadmapStep]