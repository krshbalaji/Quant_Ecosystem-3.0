from quant_ecosystem.temporal.temporal_memory import (
    temporal_memory,
)


class EraAnalyzer:

    def regime_distribution(self):

        events = (
            temporal_memory.history()
        )

        if not events:
            return {}

        distribution = {}

        for event in events:

            distribution[
                event.regime
            ] = (
                distribution.get(
                    event.regime,
                    0,
                )
                + 1
            )

        return distribution


era_analyzer = (
    EraAnalyzer()
)