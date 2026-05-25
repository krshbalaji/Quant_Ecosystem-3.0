from quant_ecosystem.research import (
    TechnicalSignal,
    FactorSignal,
)

from quant_ecosystem.research.research_pipeline import (
    research_pipeline,
)


BENCHMARK = list(range(100, 140))


def test_pipeline():
    signals = {
        "SBIN": [
            TechnicalSignal(
                symbol="SBIN",
                signal_type="BREAKOUT",
                direction="LONG",
                confidence=80,
            ),
            FactorSignal(
                symbol="SBIN",
                factor_name="MOMENTUM",
                score=1.4,
                confidence=70,
            ),
        ],
        "INFY": [
            TechnicalSignal(
                symbol="INFY",
                signal_type="EMA",
                direction="LONG",
                confidence=60,
            )
        ],
    }

    result = research_pipeline.run(
        signals,
        benchmark_series=BENCHMARK,
    )

    assert "regime" in result
    assert len(
        result["alpha_signals"]
    ) == 2
    assert len(
        result["ranked_opportunities"]
    ) == 2