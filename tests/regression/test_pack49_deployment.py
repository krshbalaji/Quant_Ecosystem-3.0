from quant_ecosystem.deployment import (
    DeploymentConfig,
    startup_orchestrator,
    deployment_validator,
)

from quant_ecosystem.runtime import (
    lifecycle_manager,
)


def setup_function():
    lifecycle_manager.stop()


def test_validator_valid():
    cfg = DeploymentConfig(
        environment="prod",
        runtime_mode="live",
    )

    assert (
        deployment_validator.validate(cfg)
        is True
    )


def test_validator_invalid():
    cfg = DeploymentConfig(
        environment="broken",
        runtime_mode="live",
    )

    assert (
        deployment_validator.validate(cfg)
        is False
    )


def test_launch():
    cfg = DeploymentConfig(
        environment="dev",
        runtime_mode="paper",
    )

    result = startup_orchestrator.launch(
        cfg
    )

    assert result == "RUNNING"


def test_invalid_launch():
    cfg = DeploymentConfig(
        environment="bad",
        runtime_mode="live",
    )

    try:
        startup_orchestrator.launch(cfg)
        assert False
    except ValueError:
        assert True


def test_bootstrap_payload():
    from quant_ecosystem.deployment import (
        environment_bootstrap,
    )

    cfg = DeploymentConfig(
        environment="staging",
        runtime_mode="paper",
    )

    result = environment_bootstrap.bootstrap(
        cfg
    )

    assert result["bootstrapped"] is True