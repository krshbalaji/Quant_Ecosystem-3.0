from quant_ecosystem.runtime import (
    dependency_registry,
    startup_validator,
    lifecycle_manager,
)


def setup_function():
    dependency_registry.clear()
    lifecycle_manager.stop()


def test_dependency_register():
    dependency_registry.register(
        "market_data",
        object(),
    )

    assert dependency_registry.exists(
        "market_data"
    )


def test_validator_fail():
    result = startup_validator.validate()

    assert result["valid"] is False
    assert "market_data" in result["missing"]


def test_validator_pass():
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

    result = startup_validator.validate()

    assert result["valid"] is True


def test_lifecycle_start():
    lifecycle_manager.start()

    assert lifecycle_manager.state() == "RUNNING"


def test_lifecycle_restart():
    lifecycle_manager.restart()

    assert lifecycle_manager.state() == "RUNNING"