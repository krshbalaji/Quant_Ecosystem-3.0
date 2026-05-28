class ExtinctionPreventionEngine:

    def defensive_posture(
        self,
        *,
        extinction_probability,
    ):

        if extinction_probability > 0.60:
            return "MAX_DEFENSE"

        if extinction_probability > 0.40:
            return "ELEVATED_DEFENSE"

        return "NORMAL"


extinction_prevention_engine = (
    ExtinctionPreventionEngine()
)