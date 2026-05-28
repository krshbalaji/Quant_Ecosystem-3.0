class UncertaintyGovernor:

    def posture(
        self,
        *,
        uncertainty_score,
    ):

        if uncertainty_score >= 0.70:
            return "MINIMAL"

        if uncertainty_score >= 0.40:
            return "REDUCED"

        return "NORMAL"


uncertainty_governor = (
    UncertaintyGovernor()
)