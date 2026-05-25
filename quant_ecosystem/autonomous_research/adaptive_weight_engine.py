class AdaptiveWeightEngine:

    def adjust_weight(
        self,
        base_weight,
        win_rate,
        confidence,
    ):
        multiplier = 1.0

        if win_rate >= 70:
            multiplier += 0.30
        elif win_rate >= 55:
            multiplier += 0.15
        elif win_rate <= 35:
            multiplier -= 0.25

        if confidence >= 80:
            multiplier += 0.10
        elif confidence <= 30:
            multiplier -= 0.10

        adjusted = base_weight * multiplier

        if adjusted < 0:
            adjusted = 0

        return round(adjusted, 4)


adaptive_weight_engine = (
    AdaptiveWeightEngine()
)