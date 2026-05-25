class SignalDecayEngine:

    def confidence_decay(
        self,
        original_confidence,
        age_hours,
        decay_per_hour=2.0,
    ):
        decayed = (
            original_confidence
            - (age_hours * decay_per_hour)
        )

        if decayed < 0:
            decayed = 0

        return round(decayed, 2)

    def classify(
        self,
        confidence,
    ):
        if confidence <= 20:
            return "EXPIRED"

        if confidence <= 50:
            return "WEAK"

        return "ACTIVE"


signal_decay_engine = (
    SignalDecayEngine()
)