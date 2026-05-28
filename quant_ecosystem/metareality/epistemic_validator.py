class EpistemicValidator:

    def trustworthy(
        self,
        *,
        confidence_score,
        blindspot_risk,
    ):

        return (
            confidence_score >= 0.25
            and blindspot_risk <= 0.70
        )


epistemic_validator = (
    EpistemicValidator()
)