from quant_ecosystem.research import (
    ResearchHypothesis,
    TechnicalSignal,
)

from quant_ecosystem.research.signal_persistence import (
    signal_persistence_layer,
)


def setup_function():
    signal_persistence_layer.clear()


def test_record_signal():
    signal = TechnicalSignal(
        symbol="SBIN",
        signal_type="BREAKOUT",
        direction="LONG",
        confidence=80,
    )

    signal_persistence_layer.record_signal(
        signal
    )

    journal = (
        signal_persistence_layer
        .signal_journal()
    )

    assert len(journal) == 1


def test_archive_hypothesis():
    hypothesis = ResearchHypothesis(
        hypothesis_id="H1",
        title="Trend continuation",
        thesis="Momentum thesis",
    )

    signal_persistence_layer.archive_hypothesis(
        hypothesis
    )

    archive = (
        signal_persistence_layer
        .hypothesis_archive()
    )

    assert len(archive) == 1


def test_audit_trail():
    signal = TechnicalSignal(
        symbol="INFY",
        signal_type="EMA",
        direction="LONG",
        confidence=70,
    )

    signal_persistence_layer.record_signal(
        signal
    )

    audit = (
        signal_persistence_layer
        .audit_trail()
    )

    assert len(audit) == 1
    assert audit[0]["event"] == (
        "SIGNAL_RECORDED"
    )


def test_replay_ledger():
    signal = TechnicalSignal(
        symbol="TCS",
        signal_type="MOMENTUM",
        direction="SHORT",
        confidence=65,
    )

    signal_persistence_layer.record_signal(
        signal
    )

    replay = (
        signal_persistence_layer
        .replay_ledger()
    )

    assert len(replay) == 1