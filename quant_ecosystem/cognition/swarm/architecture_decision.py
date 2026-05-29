from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDecision:
    decision_id: str
    category_name: str