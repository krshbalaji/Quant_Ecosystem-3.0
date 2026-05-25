from quant_ecosystem.research import (
    RankedOpportunity,
    signal_confidence_engine,
)


class AlphaScoringEngine:

    REGIME_MULTIPLIERS = {
        "TREND_VOL": 1.20,
        "TREND_LOWVOL": 1.10,
        "MEANREV_VOL": 0.90,
        "MEANREV_LOWVOL": 1.00,
    }

    def conviction_weight(
        self,
        confidence,
    ):
        conviction = (
            signal_confidence_engine
            .conviction(confidence)
        )

        mapping = {
            "HIGH": 1.25,
            "MEDIUM": 1.00,
            "LOW": 0.75,
            "WEAK": 0.50,
        }

        return mapping[conviction]

    def regime_multiplier(
        self,
        regime,
    ):
        return self.REGIME_MULTIPLIERS.get(
            regime,
            1.0,
        )

    def alpha_score(
        self,
        alpha_signal,
        regime,
    ):
        base = float(
            alpha_signal.confidence
        )

        conviction = (
            self.conviction_weight(base)
        )

        regime_adj = (
            self.regime_multiplier(regime)
        )

        return (
            base
            * conviction
            * regime_adj
        )

    def rank(
        self,
        alpha_signals,
        regime="TREND_LOWVOL",
    ):
        ranked = []

        for signal in alpha_signals:
            score = self.alpha_score(
                signal,
                regime,
            )

            ranked.append(
                RankedOpportunity(
                    symbol=signal.symbol,
                    alpha_score=score,
                    confidence=signal.confidence,
                    metadata={
                        "direction": signal.direction,
                        "regime": regime,
                    },
                )
            )

        ranked = sorted(
            ranked,
            key=lambda x: x.alpha_score,
            reverse=True,
        )

        for idx, item in enumerate(
            ranked,
            start=1,
        ):
            item.rank = idx

        return ranked

    def shortlist(
        self,
        ranked,
        top_n=5,
    ):
        return ranked[:top_n]


alpha_scoring_engine = (
    AlphaScoringEngine()
)