from dataclasses import dataclass, field


@dataclass
class DomainEvent:
    name: str
    payload: dict
    metadata: dict = field(default_factory=dict)