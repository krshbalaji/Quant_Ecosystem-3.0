from quant_ecosystem.autonomous_research import (
    signal_decay_engine,
    opportunity_aging_engine,
    research_memory,
)


def setup_function():
    research_memory.clear()


def test_decay():
    result = (
        signal_decay_engine
        .confidence_decay(
            80,
            10,
        )
    )

    assert result == 60


def test_decay_classification():
    result = (
        signal_decay_engine
        .classify(10)
    )

    assert result == "EXPIRED"


def test_aging_evaluate():
    result = (
        opportunity_aging_engine
        .evaluate(
            80,
            40,
        )
    )

    assert result["retire"] is True


def test_memory_record():
    research_memory.record(
        "sig_1",
        80,
    )

    result = (
        research_memory.fetch(
            "sig_1"
        )
    )

    assert result is not None


def test_memory_outcome():
    research_memory.record(
        "sig_2",
        70,
        "WIN",
    )

    result = (
        research_memory.fetch(
            "sig_2"
        )
    )

    assert result["outcome"] == "WIN"