class ContinuityGuardian:

    def survivable(
        self,
        *,
        extinction_probability,
        continuity_risk,
    ):

        return (
            extinction_probability < 0.75
            and continuity_risk < 0.50
        )


continuity_guardian = (
    ContinuityGuardian()
)