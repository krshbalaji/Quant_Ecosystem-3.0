from dataclasses import dataclass


@dataclass
class ConsensusVote:

    source: str

    approved: bool

    confidence: float