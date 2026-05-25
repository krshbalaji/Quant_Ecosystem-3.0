from quant_ecosystem.configuration import (
    RuntimeConfig,
    environment_profiles,
    config_validator,
)


def test_dev_profile():
    cfg = environment_profiles.dev()

    assert cfg.environment == "DEV"
    assert cfg.mode == "PAPER"


def test_prod_profile():
    cfg = environment_profiles.prod()

    assert cfg.environment == "PROD"
    assert cfg.mode == "LIVE"


def test_valid_config():
    cfg = RuntimeConfig(
        environment="DEV",
        broker="SIM",
        mode="PAPER",
    )

    result = config_validator.validate(cfg)

    assert result["valid"] is True


def test_invalid_env():
    cfg = RuntimeConfig(
        environment="XXX",
        broker="SIM",
        mode="PAPER",
    )

    result = config_validator.validate(cfg)

    assert result["valid"] is False


def test_invalid_mode():
    cfg = RuntimeConfig(
        environment="DEV",
        broker="SIM",
        mode="BROKEN",
    )

    result = config_validator.validate(cfg)

    assert result["valid"] is False