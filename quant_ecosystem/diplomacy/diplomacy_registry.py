class DiplomacyRegistry:

    def __init__(self):

        self._proposals = []

    def register(
        self,
        proposal,
    ):

        self._proposals.append(
            proposal
        )

    def proposals(self):

        return list(
            self._proposals
        )

    def clear(self):

        self._proposals.clear()


diplomacy_registry = (
    DiplomacyRegistry()
)