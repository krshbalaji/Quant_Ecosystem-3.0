class SignalConfidenceEngine:

    def normalize(
        self,
        confidence,
    ):
        confidence = float(confidence)

        if confidence < 0:
            return 0.0

        if confidence > 100:
            return 100.0

        return confidence

    def weighted_confidence(
        self,
        confidence_weights,
    ):
        if not confidence_weights:
            return 0.0

        total_weight = sum(
            weight
            for _, weight in confidence_weights
        )

        if total_weight == 0:
            return 0.0

        total = 0.0

        for confidence, weight in (
            confidence_weights
        ):
            total += (
                self.normalize(confidence)
                * weight
            )

        return total / total_weight

    def conviction(
        self,
        confidence,
    ):
        confidence = self.normalize(
            confidence
        )

        if confidence >= 80:
            return "HIGH"

        if confidence >= 60:
            return "MEDIUM"

        if confidence >= 40:
            return "LOW"

        return "WEAK"


signal_confidence_engine = (
    SignalConfidenceEngine()
)