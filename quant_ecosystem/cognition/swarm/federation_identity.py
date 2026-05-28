from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class FederationIdentity:
    organism_id: str
    constitutional_hash: str
    diplomatic_tier: str = "neutral"
    federation_tags: List[str] = field(default_factory=list)
    capabilities: Dict[str, float] = field(default_factory=dict)

    def is_trusted_for(self, capability: str) -> bool:
        return self.capabilities.get(capability, 0.0) >= 0.5