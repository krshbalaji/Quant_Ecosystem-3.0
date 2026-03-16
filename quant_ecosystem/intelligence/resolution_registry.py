from dataclasses import dataclass
from typing import Dict


@dataclass
class ResolutionConfig:
    timeframe: str
    research_intensity: int
    promotion_threshold: float
    capital_weight: float
    validation_weight: float


class ResolutionRegistry:

    def __init__(self):
        self._resolutions: Dict[str, ResolutionConfig] = {}
        self._build_default_registry()

    def _build_default_registry(self):

        self.register(
            ResolutionConfig("M5", research_intensity=2,
                             promotion_threshold=-0.4,
                             capital_weight=0.2,
                             validation_weight=0.2)
        )

        self.register(
            ResolutionConfig("M15", research_intensity=4,
                             promotion_threshold=-0.3,
                             capital_weight=0.3,
                             validation_weight=0.3)
        )

        self.register(
            ResolutionConfig("H1", research_intensity=3,
                             promotion_threshold=-0.25,
                             capital_weight=0.3,
                             validation_weight=0.3)
        )

        self.register(
            ResolutionConfig("D1", research_intensity=1,
                             promotion_threshold=-0.2,
                             capital_weight=0.2,
                             validation_weight=0.2)
        )

    def register(self, config: ResolutionConfig):
        self._resolutions[config.timeframe] = config

    def get(self, timeframe: str) -> ResolutionConfig:
        return self._resolutions[timeframe]

    def all(self):
        return self._resolutions.values()
    
    def list_active_resolutions(self):
        """
        Institutional orchestrator interface.

        Returns ordered list of active research horizons.
        """
        return list(self._resolutions.keys())