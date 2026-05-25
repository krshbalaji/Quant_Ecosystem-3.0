from quant_ecosystem.backtest.walkforward_engine import (
    walkforward_engine,
)


SERIES = list(range(100))


def dummy_scorer(
    train,
    test,
):
    return len(train) + len(test)


def test_split():
    train, test = (
        walkforward_engine
        .split(SERIES)
    )

    assert len(train) == 70
    assert len(test) == 30


def test_rolling_windows():
    result = (
        walkforward_engine
        .rolling_windows(
            SERIES,
            train_size=20,
            test_size=10,
        )
    )

    assert len(result) > 0
    assert len(
        result[0]["train"]
    ) == 20
    assert len(
        result[0]["test"]
    ) == 10


def test_snapshot():
    result = (
        walkforward_engine
        .robustness_snapshot(
            [
                {"score": 10},
                {"score": 20},
                {"score": 30},
            ]
        )
    )

    assert result["avg_score"] == 20


def test_run():
    result = (
        walkforward_engine
        .run(
            SERIES,
            dummy_scorer,
        )
    )

    assert "snapshot" in result
    assert (
        result["snapshot"]["windows"]
        > 0
    )