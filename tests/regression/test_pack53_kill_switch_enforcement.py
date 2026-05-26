from quant_ecosystem.execution.execution_router import (
    ExecutionRouter,
)


class CountingBroker:
    def __init__(self):
        self.calls = 0

    def place_order(self, **kwargs):
        self.calls += 1
        return {
            "status": "TRADE",
            "order_id": "LIVE-001",
        }

    def get_orders(self):
        return []


def build_router():
    broker = CountingBroker()
    router = ExecutionRouter(
        broker=broker,
        mode="LIVE",
    )
    return router, broker


def test_kill_switch_blocks_execution():
    router, broker = build_router()

    msg = router.kill_switch()

    result = router.submit_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
    )

    assert "Kill switch" in msg
    assert broker.calls == 0
    assert result["status"] == "SKIPPED"


def test_stop_trading_blocks_execution():
    router, broker = build_router()

    router.stop_trading()

    result = router.submit_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
    )

    assert broker.calls == 0
    assert result["status"] == "SKIPPED"


def test_start_trading_reenables_execution():
    router, broker = build_router()

    router.stop_trading()
    router.start_trading()

    result = router.submit_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
    )

    assert broker.calls == 1


def test_kill_switch_persists_until_restart():
    router, broker = build_router()

    router.kill_switch()
    router.start_trading()

    result = router.submit_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
    )

    assert broker.calls == 0
    assert result["status"] == "SKIPPED"