from unittest.mock import patch
from quant_ecosystem.broker.fyers_broker import FyersBroker


class FakeAdapter:
    def login(self):
        return True

    def get_funds(self):
        return {
            "code": 200,
            "fund_limit": []
        }

    def get_positions(self):
        return {
            "code": 200,
            "netPositions": []
        }

    def get_account_snapshot(self):
        return {
            "account_source": "FYERS_LIVE"
        }


def test_token_refresh_path():
    broker = FyersBroker()

    with patch(
        "quant_ecosystem.broker.fyers_broker.FyersTokenManager"
    ) as mgr_cls:

        with patch(
            "quant_ecosystem.broker.adapters.fyers_adapter.FyersAdapter"
        ) as adapter_cls:

            adapter_cls.side_effect = [
                Exception("expired"),
                FakeAdapter(),
            ]

            mgr = mgr_cls.return_value
            mgr.generate_token.return_value = "fresh_token"

            broker.connect()

            assert broker.account_source == "FYERS_LIVE"
            assert broker.live_client is not None