from dataclasses import dataclass


@dataclass
class ExecutionRationale:

    broker: str

    regime: str

    aggression: float

    consensus_approved: bool

    shard_id: str

    explanation: str