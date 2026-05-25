from quant_ecosystem.execution_intelligence import (
    broker_quality_engine,
    slippage_intelligence,
    execution_optimizer,
)


BROKERS = {
    "fyers": {
        "fill_rate": 98,
        "avg_latency_ms": 120,
        "rejection_rate": 0.01,
    },
    "groww": {
        "fill_rate": 92,
        "avg_latency_ms": 250,
        "rejection_rate": 0.03,
    },
}


def test_quality_score():
    result = (
        broker_quality_engine.score(
            98,
            120,
            0.01,
        )
    )

    assert result > 0


def test_broker_rank():
    result = (
        broker_quality_engine.rank(
            BROKERS
        )
    )

    assert result[0]["broker"] == "fyers"


def test_slippage_bps():
    result = (
        slippage_intelligence
        .estimate_bps(
            100,
            101,
        )
    )

    assert result == 100


def test_slippage_classification():
    result = (
        slippage_intelligence
        .classify(60)
    )

    assert result == "SEVERE"


def test_route_recommendation():
    result = (
        execution_optimizer
        .recommend_route(
            BROKERS
        )
    )

    assert result["broker"] == "fyers"


def test_slippage_assessment():
    result = (
        execution_optimizer
        .slippage_assessment(
            100,
            101,
        )
    )

    assert result["classification"] == "SEVERE"


def test_optimize():
    result = (
        execution_optimizer
        .optimize(
            BROKERS,
            100,
            101,
        )
    )

    assert "route" in result
    assert "slippage" in result