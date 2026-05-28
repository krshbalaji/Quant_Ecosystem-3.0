from quant_ecosystem.evolution.governance_policy import (
    GovernancePolicy,
)


class PolicyRegistry:

    def __init__(self):

        self._policy = (
            GovernancePolicy(
                aggression_bias=1.0,
                throttle_bias=1.0,
                risk_bias=1.0,
                mutation_generation=0,
            )
        )

    def current(self):

        return self._policy

    def evolve(
        self,
        policy,
    ):

        self._policy = policy


policy_registry = (
    PolicyRegistry()
)