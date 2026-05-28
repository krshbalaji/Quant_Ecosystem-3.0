from quant_ecosystem.civilization.civilization_record import (
    CivilizationRecord,
)

from quant_ecosystem.civilization.civilization_archive import (
    civilization_archive,
)


class CivilizationEngine:

    def preserve_era(
        self,
        *,
        era_name,
        governance_generation,
        survivability_score,
        doctrine_state,
        dominant_regime,
    ):

        record = (
            CivilizationRecord(
                era_name=era_name,
                governance_generation=(
                    governance_generation
                ),
                survivability_score=(
                    survivability_score
                ),
                doctrine_state=(
                    doctrine_state
                ),
                dominant_regime=(
                    dominant_regime
                ),
            )
        )

        civilization_archive.preserve(
            record
        )


civilization_engine = (
    CivilizationEngine()
)