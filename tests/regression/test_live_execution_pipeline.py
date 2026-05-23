from quant_ecosystem.execution.execution_router import ExecutionRouter


class LiveBroker:
    def place_order(self, **kwargs):
        return {
            "status": "TRADE",
            "order_id": "LIVE001",
            "symbol": kwargs["symbol"],
            "qty": kwargs["qty"],
        }

    def get_orders(self):
        return [
            {"id": "LIVE001"}
        ]
        
class Risk:
    def approve_trade(self, *args, **kwargs):
        return True


class State:
    trading_mode = "LIVE"


class Market:
    pass


class Strategy:
    pass


class Portfolio:
    pass


def test_end_to_end_execution_pipeline():
    er = ExecutionRouter(
        broker=LiveBroker(),
        risk_engine=Risk(),
        state=State(),
        market_data=Market(),
        strategy_engine=Strategy(),
        portfolio_engine=Portfolio(),
        mode="LIVE",
    )

    signal = {
        "symbol": "NSE:SBIN-EQ",
        "side": "BUY",
        "price": 800,
        "confidence": 0.95,
        "volatility": 1.0,
        "strategy_id": "pipeline_test",
        "forced_qty": 1,
    }

    result = er.execute_trade(
        signal=signal,
        market_bias="BULLISH",
        regime="TREND",
    )

    assert result["status"] == "TRADE"
    assert result["symbol"] == "NSE:SBIN-EQ"
    assert result["qty"] == 1