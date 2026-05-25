class SlippageIntelligence:

    def estimate_bps(
        self,
        expected_price,
        actual_price,
    ):
        deviation = abs(
            actual_price
            - expected_price
        )

        return (
            deviation
            / expected_price
        ) * 10000

    def classify(
        self,
        bps,
    ):
        if bps >= 50:
            return "SEVERE"

        if bps >= 20:
            return "HIGH"

        if bps >= 5:
            return "WATCH"

        return "NORMAL"


slippage_intelligence = (
    SlippageIntelligence()
)