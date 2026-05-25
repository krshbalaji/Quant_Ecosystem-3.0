from quant_ecosystem.persistence import (
    event_store,
    state_repository,
)


def setup_function():
    event_store.clear()
    state_repository.clear()


def test_event_append():
    event_store.append(
        "ORDER_CREATED",
        {"id": 1},
    )

    assert len(
        event_store.all_events()
    ) == 1


def test_event_filter():
    event_store.append(
        "ORDER_CREATED",
        {},
    )

    event_store.append(
        "ORDER_FILLED",
        {},
    )

    result = (
        event_store.by_type(
            "ORDER_CREATED"
        )
    )

    assert len(result) == 1


def test_state_save():
    state_repository.save(
        "risk_state",
        "NORMAL",
    )

    assert (
        state_repository.load(
            "risk_state"
        )
        == "NORMAL"
    )


def test_state_delete():
    state_repository.save(
        "x",
        1,
    )

    state_repository.delete("x")

    assert (
        state_repository.load("x")
        is None
    )


def test_snapshot():
    state_repository.save(
        "cpu",
        55,
    )

    snap = (
        state_repository.snapshot()
    )

    assert snap["cpu"] == 55