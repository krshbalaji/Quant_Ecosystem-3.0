from quant_ecosystem.execution.execution_router import ExecutionRouter


class DummyBroker:
    def place_order(self, **kwargs):
        return {
            "status": "TRADE",
            "order_id": "TEST123",
            "symbol": kwargs["symbol"],
            "qty": kwargs["qty"],
        }


class DummyRisk:
    def approve_trade(self, *args, **kwargs):
        return True


class DummyState:
    trading_mode = "LIVE"


class DummyMarket:
    pass


class DummyStrategy:
    pass


class DummyPortfolio:
    pass


def test_forced_qty_bypasses_position_sizer():
    er = ExecutionRouter(
        broker=DummyBroker(),
        risk_engine=DummyRisk(),
        state=DummyState(),
        market_data=DummyMarket(),
        strategy_engine=DummyStrategy(),
        portfolio_engine=DummyPortfolio(),
        mode="LIVE",
    )

    signal = {
        "symbol": "NSE:SBIN-EQ",
        "side": "BUY",
        "price": 800,
        "confidence": 0.95,
        "volatility": 1.0,
        "strategy_id": "forced_qty_test",
        "forced_qty": 1,
    }

    result = er.execute_trade(
        signal=signal,
        market_bias="BULLISH",
        regime="TREND",
    )

    assert result["qty"] == 1