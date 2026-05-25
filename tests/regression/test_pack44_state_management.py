from quant_ecosystem.state import (
    state_manager,
    state_transition_controller,
    state_snapshot_engine,
    state_restore_engine,
)


def setup_function():
    state_manager.clear()


def test_state_set_get():
    state_manager.set(
        "risk",
        "NORMAL",
    )

    assert (
        state_manager.get("risk")
        == "NORMAL"
    )


def test_transition():
    state_manager.set(
        "mode",
        "PAPER",
    )

    result = (
        state_transition_controller
        .transition(
            "mode",
            "LIVE",
        )
    )

    assert result["previous"] == "PAPER"
    assert result["current"] == "LIVE"


def test_snapshot():
    state_manager.set(
        "cpu",
        70,
    )

    snap = (
        state_snapshot_engine.capture()
    )

    assert snap["cpu"] == 70


def test_restore():
    state_manager.set(
        "x",
        1,
    )

    snap = state_manager.snapshot()

    state_manager.clear()

    state_restore_engine.restore(
        snap
    )

    assert state_manager.get("x") == 1


def test_clear():
    state_manager.set(
        "temp",
        99,
    )

    state_manager.clear()

    assert (
        state_manager.get("temp")
        is None
    )