from quant_ecosystem.execution_intelligence import (
    broker_memory,
    execution_learning_engine,
)


def setup_function():
    broker_memory.clear()


def test_record_execution():
    broker_memory.record_execution(
        "fyers",
        12,
        True,
    )

    assert (
        broker_memory.average_slippage(
            "fyers"
        )
        == 12
    )


def test_success_rate():
    broker_memory.record_execution(
        "fyers",
        10,
        True,
    )

    broker_memory.record_execution(
        "fyers",
        20,
        False,
    )

    result = (
        broker_memory.success_rate(
            "fyers"
        )
    )

    assert result == 0.5


def test_snapshot():
    broker_memory.record_execution(
        "groww",
        8,
        True,
    )

    result = (
        broker_memory.broker_snapshot(
            "groww"
        )
    )

    assert "avg_slippage" in result


def test_trust_score():
    broker_memory.record_execution(
        "fyers",
        10,
        True,
    )

    result = (
        execution_learning_engine
        .trust_score(
            "fyers"
        )
    )

    assert result > 0


def test_adaptive_rank():
    broker_memory.record_execution(
        "fyers",
        5,
        True,
    )

    broker_memory.record_execution(
        "groww",
        30,
        False,
    )

    result = (
        execution_learning_engine
        .adaptive_rank(
            [
                "fyers",
                "groww",
            ]
        )
    )

    assert result[0]["broker"] == "fyers"