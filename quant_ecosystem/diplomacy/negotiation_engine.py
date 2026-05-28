from quant_ecosystem.diplomacy.negotiation_proposal import (
    NegotiationProposal,
)

from quant_ecosystem.diplomacy.diplomacy_registry import (
    diplomacy_registry,
)


class NegotiationEngine:

    def propose(
        self,
        *,
        source,
        preference,
        priority,
    ):

        diplomacy_registry.register(
            NegotiationProposal(
                source=source,
                preference=(
                    preference
                ),
                priority=priority,
            )
        )

    def resolve(self):

        proposals = (
            diplomacy_registry
            .proposals()
        )

        if not proposals:

            return "NEUTRAL"

        winner = max(
            proposals,
            key=lambda p: (
                p.priority
            ),
        )

        diplomacy_registry.clear()

        return winner.preference


negotiation_engine = (
    NegotiationEngine()
)