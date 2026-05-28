from quant_ecosystem.evolution.policy_registry import (
    policy_registry,
)


class DoctrineEngine:

    def aggression_bias(self):

        return (
            policy_registry
            .current()
            .aggression_bias
        )

    def throttle_bias(self):

        return (
            policy_registry
            .current()
            .throttle_bias
        )

    def risk_bias(self):

        return (
            policy_registry
            .current()
            .risk_bias
        )


doctrine_engine = (
    DoctrineEngine()
)