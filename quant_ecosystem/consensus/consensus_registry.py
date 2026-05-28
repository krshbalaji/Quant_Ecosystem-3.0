class ConsensusRegistry:

    def __init__(self):

        self._votes = []

    def register(
        self,
        vote,
    ):

        self._votes.append(
            vote
        )

    def clear(self):

        self._votes.clear()

    def votes(self):

        return list(
            self._votes
        )


consensus_registry = (
    ConsensusRegistry()
)