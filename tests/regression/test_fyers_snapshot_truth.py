from quant_ecosystem.broker.adapters.fyers_adapter import FyersAdapter


class FakeClient:
    def funds(self):
        return {
            "fund_limit": [
                {"title": "Available Balance", "equityAmount": 0}
            ]
        }

    def positions(self):
        return {
            "netPositions": [],
            "overall": {
                "pl_realized": 0
            }
        }

    def orderbook(self):
        return {"orderBook": []}

    def tradebook(self):
        return {"tradeBook": []}

    def holdings(self):
        return {
            "holdings": [
                {
                    "symbol": "NSE:ASHOKLEY-EQ",
                    "marketVal": 1582.1000000000001,
                    "pl": -310.60000000000002,
                    "ltp": 158.21,
                    "costPrice": 189.27,
                },
                {
                    "symbol": "NSE:ITC-EQ",
                    "marketVal": 301.7,
                    "pl": -39.800000000000004,
                    "ltp": 301.7,
                    "costPrice": 341.5,
                },
            ]
        }


def test_snapshot_truth():
    adapter = FyersAdapter(app_id="x", access_token="y")
    adapter.client = FakeClient()

    snap = adapter.get_account_snapshot()

    assert snap["account_source"] == "FYERS_LIVE"
    assert snap["cash_balance"] == 0.0
    assert snap["unrealized_pnl"] == -350.4
    assert snap["equity"] == 1883.8
    assert len(snap["holdings"]) == 2
    assert snap["holdings"][0]["marketVal"] == 1582.1
    assert snap["holdings"][1]["pl"] == -39.8