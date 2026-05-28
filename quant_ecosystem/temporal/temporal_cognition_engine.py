from datetime import datetime

from quant_ecosystem.temporal.temporal_event import (
    TemporalEvent,
)

from quant_ecosystem.temporal.temporal_memory import (
    temporal_memory,
)


class TemporalCognitionEngine:

    def remember(
        self,
        *,
        regime,
        survivability,
        stress_level,
        policy_generation,
    ):

        event = (
            TemporalEvent(
                timestamp=str(
                    datetime.utcnow()
                ),
                regime=regime,
                survivability=(
                    survivability
                ),
                stress_level=(
                    stress_level
                ),
                policy_generation=(
                    policy_generation
                ),
            )
        )

        temporal_memory.record(
            event
        )

    def latest(self):

        return (
            temporal_memory.latest()
        )


temporal_cognition_engine = (
    TemporalCognitionEngine()
)