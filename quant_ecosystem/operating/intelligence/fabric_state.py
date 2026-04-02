from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FabricState:
    """
    Institutional research fabric global intelligence state.

    This object becomes the shared situational awareness layer
    across all resolution research organisms.
    """

    research_load_per_resolution: Dict[str, float] = field(default_factory=dict)
    alpha_yield_per_resolution: Dict[str, float] = field(default_factory=dict)
    promotion_rate_per_resolution: Dict[str, float] = field(default_factory=dict)

    compute_pressure: float = 0.0
    live_alpha_dependency: float = 0.0
    regime_alignment_score: float = 0.0

    def register_resolution(self, resolution: str):
        self.research_load_per_resolution.setdefault(resolution, 0.0)
        self.alpha_yield_per_resolution.setdefault(resolution, 0.0)
        self.promotion_rate_per_resolution.setdefault(resolution, 0.0)