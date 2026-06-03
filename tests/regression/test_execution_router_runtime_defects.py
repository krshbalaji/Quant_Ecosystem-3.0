from quant_ecosystem.execution.execution_router import ExecutionRouter


def test_market_regime_detector_loads():
    router = ExecutionRouter()
    detector = router._load_candle_pattern()
    assert detector is not None


def test_strategy_authority_gate_handles_registered_strategy():
    router = ExecutionRouter()
    # build minimal mocks here
    # verify no NameError path


def test_liquidation_assist_returns_none_when_disabled():
    router = ExecutionRouter()
    router.config = type("Cfg", (), {})()
    router.config.liquidation_assist_enabled = False

    assert router._maybe_liquidation_assist(
        trigger_reason="test",
        regime="NORMAL",
    ) is None