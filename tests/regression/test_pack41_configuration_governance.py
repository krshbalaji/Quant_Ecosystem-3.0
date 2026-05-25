from quant_ecosystem.configuration import (
    config_loader,
    runtime_override_engine,
    effective_config_snapshot,
)


def test_load_dev():
    cfg = config_loader.load("DEV")

    assert cfg.environment == "DEV"


def test_load_prod():
    cfg = config_loader.load("PROD")

    assert cfg.mode == "LIVE"


def test_override():
    cfg = config_loader.load("DEV")

    updated = runtime_override_engine.apply(
        cfg,
        broker="FYERS",
        mode="LIVE",
    )

    assert updated.broker == "FYERS"
    assert updated.mode == "LIVE"


def test_snapshot():
    cfg = config_loader.load("DEV")

    snap = effective_config_snapshot.snapshot(cfg)

    assert snap["environment"] == "DEV"


def test_invalid_environment():
    try:
        config_loader.load("BROKEN")
        assert False
    except ValueError:
        assert True