from dataclasses import dataclass


@dataclass
class NegotiationProposal:

    source: str

    preference: str

    priority: float