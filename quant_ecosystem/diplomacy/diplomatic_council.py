from quant_ecosystem.diplomacy.negotiation_engine import (
    negotiation_engine,
)


class DiplomaticCouncil:

    def deliberate(
        self,
        *,
        survivability,
        stress_level,
    ):

        negotiation_engine.propose(
            source="SURVIVAL",
            preference="DEFENSIVE",
            priority=(
                1.0 - stress_level
            ),
        )

        negotiation_engine.propose(
            source="OPPORTUNITY",
            preference="AGGRESSIVE",
            priority=(
                survivability
            ),
        )

        return (
            negotiation_engine
            .resolve()
        )


diplomatic_council = (
    DiplomaticCouncil()
)