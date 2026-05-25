from quant_ecosystem.portfolio.factor_intelligence import (
    portfolio_factor_intelligence,
)


class RegimeDetectionEngine:

    def trend_strength(
        self,
        series,
        lookback=20,
    ):
        if (
            not series
            or len(series) <= lookback
        ):
            return 0.0

        start = float(
            series[-lookback - 1]
        )

        end = float(series[-1])

        if start == 0:
            return 0.0

        return abs(
            ((end - start) / start)
            * 100.0
        )

    def volatility_regime(
        self,
        series,
        threshold=0.20,
    ):
        vol = (
            portfolio_factor_intelligence
            .rolling_volatility(series)
        )

        if vol >= threshold:
            return "VOLATILE"

        return "LOW_VOL"

    def trend_regime(
        self,
        series,
        threshold=5.0,
    ):
        strength = self.trend_strength(
            series
        )

        if strength >= threshold:
            return "TRENDING"

        return "MEAN_REVERTING"

    def regime_confidence(
        self,
        series,
    ):
        trend = self.trend_strength(
            series
        )

        vol = (
            portfolio_factor_intelligence
            .rolling_volatility(series)
        )

        confidence = trend + (
            vol * 10
        )

        if confidence > 100:
            return 100.0

        return confidence

    def detect(
        self,
        series,
    ):
        trend = self.trend_regime(
            series
        )

        vol = self.volatility_regime(
            series
        )

        if (
            trend == "TRENDING"
            and vol == "VOLATILE"
        ):
            regime = "TREND_VOL"

        elif (
            trend == "TRENDING"
            and vol == "LOW_VOL"
        ):
            regime = "TREND_LOWVOL"

        elif (
            trend == "MEAN_REVERTING"
            and vol == "VOLATILE"
        ):
            regime = "MEANREV_VOL"

        else:
            regime = "MEANREV_LOWVOL"

        return {
            "regime": regime,
            "trend_state": trend,
            "vol_state": vol,
            "confidence": (
                self.regime_confidence(
                    series
                )
            ),
        }


regime_detection_engine = (
    RegimeDetectionEngine()
)