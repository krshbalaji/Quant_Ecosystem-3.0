from dataclasses import dataclass


@dataclass
class GovernancePolicy:

    aggression_bias: float

    throttle_bias: float

    risk_bias: float

    mutation_generation: int