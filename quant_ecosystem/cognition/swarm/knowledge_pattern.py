from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgePattern:
    category: str
    frequency: int