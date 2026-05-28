class SurvivabilityEngine:

    def acceptable(
        self,
        *,
        survivability,
        stress_level,
    ):

        return (
            survivability >= 0.20
            and stress_level <= 0.80
        )


survivability_engine = (
    SurvivabilityEngine()
)