from quant_ecosystem.runtime import (
    dependency_registry,
    lifecycle_manager,
    readiness_engine,
    runtime_supervisor,
    autonomous_restart_controller,
)


def setup_function():
    dependency_registry.clear()
    lifecycle_manager.stop()


def test_readiness_false():
    assert readiness_engine.ready() is False


def test_readiness_true():
    dependency_registry.register(
        "market_data",
        object(),
    )
    dependency_registry.register(
        "execution",
        object(),
    )
    dependency_registry.register(
        "risk",
        object(),
    )

    assert readiness_engine.ready() is True


def test_supervisor_stable():
    result = runtime_supervisor.supervise(
        healthy=True
    )

    assert result == "STABLE"


def test_supervisor_restart():
    result = runtime_supervisor.supervise(
        healthy=False
    )

    assert result == "RESTARTED"


def test_autonomous_recovery():
    result = (
        autonomous_restart_controller
        .recover(
            healthy=False
        )
    )

    assert result == "RESTARTED"