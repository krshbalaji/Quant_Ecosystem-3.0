from quant_ecosystem.research import (
    AlphaSignal,
    RankedOpportunity,
    signal_confidence_engine,
)


class SignalFusionEngine:

    def resolve_direction(
        self,
        signals,
    ):
        long_score = 0.0
        short_score = 0.0

        for signal in signals:
            confidence = float(
                getattr(
                    signal,
                    "confidence",
                    0.0,
                )
            )

            direction = getattr(
                signal,
                "direction",
                None,
            )

            if direction == "LONG":
                long_score += confidence

            elif direction == "SHORT":
                short_score += confidence

        if long_score >= short_score:
            return "LONG"

        return "SHORT"

    def fused_confidence(
        self,
        signals,
    ):
        if not signals:
            return 0.0

        weights = []

        equal_weight = (
            1.0 / len(signals)
        )

        for signal in signals:
            weights.append(
                (
                    getattr(
                        signal,
                        "confidence",
                        0.0,
                    ),
                    equal_weight,
                )
            )

        return (
            signal_confidence_engine
            .weighted_confidence(
                weights
            )
        )

    def fuse(
        self,
        symbol,
        signals,
    ):
        if not signals:
            return None

        direction = self.resolve_direction(
            signals
        )

        confidence = self.fused_confidence(
            signals
        )

        return AlphaSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            source_signals=signals,
            metadata={
                "signal_count": len(signals)
            },
        )

    def rank_opportunities(
        self,
        alpha_signals,
    ):
        ranked = sorted(
            alpha_signals,
            key=lambda x: x.confidence,
            reverse=True,
        )

        result = []

        for idx, signal in enumerate(
            ranked,
            start=1,
        ):
            result.append(
                RankedOpportunity(
                    symbol=signal.symbol,
                    alpha_score=signal.confidence,
                    confidence=signal.confidence,
                    rank=idx,
                    metadata={
                        "direction": signal.direction
                    },
                )
            )

        return result


signal_fusion_engine = (
    SignalFusionEngine()
)