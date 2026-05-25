from quant_ecosystem.persistence import (
    event_store,
    audit_repo,
    replay_recovery_engine,
)


def setup_function():
    event_store.clear()
    audit_repo.clear()


def test_audit_record():
    audit_repo.record(
        "EXECUTION_START",
        {"mode": "LIVE"},
    )

    assert len(audit_repo.all_records()) == 1


def test_audit_filter():
    audit_repo.record(
        "ORDER",
        {},
    )

    audit_repo.record(
        "RISK",
        {},
    )

    result = audit_repo.by_event("ORDER")

    assert len(result) == 1


def test_replay_count():
    event_store.append(
        "ORDER_CREATED",
        {"id": 1},
    )

    assert replay_recovery_engine.replay_count() == 1


def test_rebuild_state():
    event_store.append(
        "ORDER_CREATED",
        {"id": 99},
    )

    rebuilt = replay_recovery_engine.rebuild_state()

    assert rebuilt["ORDER_CREATED"]["id"] == 99


def test_multi_event_rebuild():
    event_store.append(
        "CPU",
        {"value": 60},
    )

    event_store.append(
        "MEMORY",
        {"value": 40},
    )

    rebuilt = replay_recovery_engine.rebuild_state()

    assert "CPU" in rebuilt
    assert "MEMORY" in rebuilt