class AnomalyDetectionEngine:

    def slippage_anomaly(
        self,
        expected_price,
        actual_price,
        threshold_bps=20,
    ):
        deviation = abs(
            actual_price - expected_price
        )

        bps = (
            deviation / expected_price
        ) * 10000

        return {
            "anomaly": (
                bps >= threshold_bps
            ),
            "bps": bps,
        }

    def fill_size_anomaly(
        self,
        expected_qty,
        actual_qty,
        tolerance=0.20,
    ):
        deviation = abs(
            actual_qty - expected_qty
        )

        ratio = deviation / expected_qty

        return {
            "anomaly": ratio >= tolerance,
            "ratio": ratio,
        }

    def exposure_anomaly(
        self,
        expected_exposure,
        actual_exposure,
        tolerance=0.25,
    ):
        deviation = abs(
            actual_exposure
            - expected_exposure
        )

        ratio = (
            deviation / expected_exposure
        )

        return {
            "anomaly": ratio >= tolerance,
            "ratio": ratio,
        }

    def classify(
        self,
        anomalies,
    ):
        count = len(
            [
                x for x in anomalies
                if x
            ]
        )

        if count >= 3:
            return "CRITICAL"

        if count == 2:
            return "HIGH"

        if count == 1:
            return "WATCH"

        return "NORMAL"

    def evaluate(
        self,
        expected_price,
        actual_price,
        expected_qty,
        actual_qty,
        expected_exposure,
        actual_exposure,
    ):
        slip = self.slippage_anomaly(
            expected_price,
            actual_price,
        )

        fill = self.fill_size_anomaly(
            expected_qty,
            actual_qty,
        )

        exposure = self.exposure_anomaly(
            expected_exposure,
            actual_exposure,
        )

        severity = self.classify(
            [
                slip["anomaly"],
                fill["anomaly"],
                exposure["anomaly"],
            ]
        )

        return {
            "slippage": slip,
            "fill": fill,
            "exposure": exposure,
            "severity": severity,
        }


anomaly_detection_engine = (
    AnomalyDetectionEngine()
)