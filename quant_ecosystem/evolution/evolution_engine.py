from quant_ecosystem.evolution.governance_policy import (
    GovernancePolicy,
)

from quant_ecosystem.evolution.policy_registry import (
    policy_registry,
)


class EvolutionEngine:

    def evolve_policy(
        self,
        *,
        success_rate,
        stress_level,
    ):

        current = (
            policy_registry.current()
        )

        aggression = (
            current.aggression_bias
        )

        throttle = (
            current.throttle_bias
        )

        risk = (
            current.risk_bias
        )

        if success_rate >= 0.8:

            aggression *= 1.05

        else:

            aggression *= 0.95

        if stress_level >= 0.7:

            throttle *= 0.90

            risk *= 0.90

        next_policy = (
            GovernancePolicy(
                aggression_bias=(
                    round(
                        aggression,
                        4,
                    )
                ),
                throttle_bias=(
                    round(
                        throttle,
                        4,
                    )
                ),
                risk_bias=(
                    round(
                        risk,
                        4,
                    )
                ),
                mutation_generation=(
                    current
                    .mutation_generation
                    + 1
                ),
            )
        )

        policy_registry.evolve(
            next_policy
        )

        return next_policy


evolution_engine = (
    EvolutionEngine()
)