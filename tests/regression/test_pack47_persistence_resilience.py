from quant_ecosystem.persistence import (
    transaction_coordinator,
    durable_snapshot_repository,
    persistence_recovery_manager,
    backend_governance,
)


def setup_function():
    durable_snapshot_repository.clear()
    transaction_coordinator.rollback()


def test_transaction_begin():
    transaction_coordinator.begin()

    assert (
        transaction_coordinator.active()
        is True
    )


def test_transaction_commit():
    transaction_coordinator.begin()

    transaction_coordinator.commit()

    assert (
        transaction_coordinator.active()
        is False
    )


def test_snapshot_recovery():
    durable_snapshot_repository.save_snapshot(
        "s1",
        {"risk": "LOW"},
    )

    snap = (
        persistence_recovery_manager
        .recover("s1")
    )

    assert snap["risk"] == "LOW"


def test_backend_allowed():
    assert (
        backend_governance.allowed(
            "sqlite"
        )
        is True
    )


def test_backend_denied():
    assert (
        backend_governance.allowed(
            "mongo"
        )
        is False
    )