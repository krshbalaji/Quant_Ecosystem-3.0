from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class FederationMemoryContract:
    contract_id: str
    permitted_memory_types: List[str] = field(default_factory=list)
    authorized_constitutions: List[str] = field(default_factory=list)

    def allows(
        self,
        memory_type: str,
        constitutional_hash: str,
    ) -> bool:

        return (
            memory_type in self.permitted_memory_types
            and constitutional_hash in self.authorized_constitutions
        )