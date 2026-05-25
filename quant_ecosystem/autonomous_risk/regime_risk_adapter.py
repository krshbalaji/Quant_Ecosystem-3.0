class RegimeRiskAdapter:

    def adjust(
        self,
        regime,
        base_risk=1.0,
    ):
        mapping = {
            "BULL": 1.20,
            "NEUTRAL": 1.00,
            "BEAR": 0.70,
            "CRISIS": 0.40,
        }

        factor = mapping.get(
            regime,
            1.0,
        )

        return round(
            base_risk * factor,
            2,
        )


regime_risk_adapter = (
    RegimeRiskAdapter()
)