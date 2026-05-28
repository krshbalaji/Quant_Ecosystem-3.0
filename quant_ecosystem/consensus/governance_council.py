from quant_ecosystem.consensus.consensus_engine import (
    consensus_engine,
)


class GovernanceCouncil:

    def evaluate(
        self,
        *,
        regime_ok,
        risk_ok,
        broker_ok,
    ):

        consensus_engine.vote(
            source="REGIME",
            approved=regime_ok,
            confidence=0.8,
        )

        consensus_engine.vote(
            source="RISK",
            approved=risk_ok,
            confidence=0.9,
        )

        consensus_engine.vote(
            source="BROKER",
            approved=broker_ok,
            confidence=0.7,
        )

        return (
            consensus_engine
            .approved()
        )


governance_council = (
    GovernanceCouncil()
)