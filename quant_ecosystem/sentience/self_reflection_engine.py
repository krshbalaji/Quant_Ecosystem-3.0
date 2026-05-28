from quant_ecosystem.sentience.self_reflection_record import (
    SelfReflectionRecord,
)

from quant_ecosystem.sentience.reflection_archive import (
    reflection_archive,
)


class SelfReflectionEngine:

    def reflect(
        self,
        *,
        mission,
        constitutional,
        survivability,
    ):

        consistency = survivability

        if not constitutional:
            consistency *= 0.50

        record = (
            SelfReflectionRecord(
                mission=mission,
                constitutional=(
                    constitutional
                ),
                survivability=(
                    survivability
                ),
                consistency_score=round(
                    consistency,
                    4,
                ),
            )
        )

        reflection_archive.remember(
            record
        )

        return record


self_reflection_engine = (
    SelfReflectionEngine()
)