from quant_ecosystem.research.signal_fusion_engine import (
    signal_fusion_engine,
)

from quant_ecosystem.research.regime_detection_engine import (
    regime_detection_engine,
)

from quant_ecosystem.research.alpha_scoring_engine import (
    alpha_scoring_engine,
)


class ResearchPipeline:

    def run(
        self,
        symbol_signal_map,
        benchmark_series=None,
    ):
        alpha_signals = []

        detected_regime = "TREND_LOWVOL"

        if benchmark_series:
            regime_result = (
                regime_detection_engine.detect(
                    benchmark_series
                )
            )

            detected_regime = (
                regime_result["regime"]
            )

        for symbol, signals in (
            symbol_signal_map.items()
        ):
            alpha = (
                signal_fusion_engine.fuse(
                    symbol,
                    signals,
                )
            )

            if alpha:
                alpha_signals.append(alpha)

        ranked = (
            alpha_scoring_engine.rank(
                alpha_signals,
                regime=detected_regime,
            )
        )

        return {
            "regime": detected_regime,
            "alpha_signals": alpha_signals,
            "ranked_opportunities": ranked,
        }


research_pipeline = ResearchPipeline()