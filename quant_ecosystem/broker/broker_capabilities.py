from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class BrokerCapabilities:
    """
    QE3 broker capability contract.

    Every broker adapter must explicitly declare what it supports.
    Router logic must rely on these capabilities instead of heuristics.
    """

    # execution lifecycle
    supports_reconciliation: bool = False
    supports_partial_fill_tracking: bool = False
    supports_cancel_order: bool = False
    supports_modify_order: bool = False
    supports_order_history: bool = False

    # account sync
    supports_positions_sync: bool = False
    supports_balance_sync: bool = False
    supports_holdings_sync: bool = False

    # market data
    supports_market_data_snapshot: bool = False
    supports_live_streaming: bool = False
    supports_ltp: bool = False
    supports_orderbook: bool = False

    # execution resilience
    supports_retry: bool = True
    supports_health_check: bool = True
    supports_rate_limit_awareness: bool = False

    # asset / geography
    supported_markets: List[str] = field(default_factory=list)
    supported_assets: List[str] = field(default_factory=list)

    # misc
    broker_name: str = "unknown"

    def supports_market(self, market: str) -> bool:
        if not self.supported_markets:
            return False
        return market.upper() in {
            m.upper() for m in self.supported_markets
        }

    def supports_asset(self, asset: str) -> bool:
        if not self.supported_assets:
            return False
        return asset.upper() in {
            a.upper() for a in self.supported_assets
        }

    def validate_route(self, market: str, asset: str) -> None:
        if not self.supports_market(market):
            raise RuntimeError(
                f"{self.broker_name} does not support market={market}"
            )

        if not self.supports_asset(asset):
            raise RuntimeError(
                f"{self.broker_name} does not support asset={asset}"
            )


# ---- canonical presets ----------------------------------------------------


FYERS_CAPABILITIES = BrokerCapabilities(
    broker_name="fyers",
    supports_reconciliation=True,
    supports_partial_fill_tracking=True,
    supports_cancel_order=True,
    supports_modify_order=True,
    supports_order_history=True,
    supports_positions_sync=True,
    supports_balance_sync=True,
    supports_holdings_sync=True,
    supports_market_data_snapshot=True,
    supports_live_streaming=True,
    supports_ltp=True,
    supports_orderbook=True,
    supports_retry=True,
    supports_health_check=True,
    supports_rate_limit_awareness=True,
    supported_markets=[
        "INDIA",
    ],
    supported_assets=[
        "EQUITY",
        "FUTURES",
        "OPTIONS",
        "COMMODITY",
        "FOREX",
    ],
)


GROWW_CAPABILITIES = BrokerCapabilities(
    broker_name="groww",
    supports_reconciliation=True,
    supports_partial_fill_tracking=True,
    supports_cancel_order=True,
    supports_modify_order=True,
    supports_order_history=True,
    supports_positions_sync=True,
    supports_balance_sync=True,
    supports_holdings_sync=True,
    supports_market_data_snapshot=True,
    supports_live_streaming=False,
    supports_ltp=True,
    supports_orderbook=True,
    supports_retry=True,
    supports_health_check=True,
    supported_markets=[
        "INDIA",
    ],
    supported_assets=[
        "EQUITY",
        "FUTURES",
        "OPTIONS",
        "ETF",
    ],
)


LEMONN_CAPABILITIES = BrokerCapabilities(
    broker_name="lemonn",
    supports_reconciliation=True,
    supports_partial_fill_tracking=True,
    supports_cancel_order=True,
    supports_modify_order=True,
    supports_order_history=True,
    supports_positions_sync=True,
    supports_balance_sync=True,
    supports_holdings_sync=True,
    supports_market_data_snapshot=True,
    supports_live_streaming=False,
    supports_ltp=True,
    supports_orderbook=True,
    supports_retry=True,
    supports_health_check=True,
    supported_markets=[
        "INDIA",
    ],
    supported_assets=[
        "EQUITY",
        "FUTURES",
        "OPTIONS",
        "ETF",
    ],
)


VIEWTRADE_CAPABILITIES = BrokerCapabilities(
    broker_name="viewtrade",
    supports_reconciliation=True,
    supports_partial_fill_tracking=True,
    supports_cancel_order=True,
    supports_modify_order=True,
    supports_order_history=True,
    supports_positions_sync=True,
    supports_balance_sync=True,
    supports_holdings_sync=True,
    supports_market_data_snapshot=True,
    supports_live_streaming=False,
    supports_ltp=True,
    supports_orderbook=False,
    supports_retry=True,
    supports_health_check=True,
    supported_markets=[
        "US",
        "GLOBAL",
    ],
    supported_assets=[
        "EQUITY",
        "ETF",
        "OPTIONS",
    ],
)


COINSWITCH_CAPABILITIES = BrokerCapabilities(
    broker_name="coinswitch",
    supports_reconciliation=True,
    supports_partial_fill_tracking=True,
    supports_cancel_order=True,
    supports_modify_order=False,
    supports_order_history=True,
    supports_positions_sync=True,
    supports_balance_sync=True,
    supports_holdings_sync=False,
    supports_market_data_snapshot=True,
    supports_live_streaming=True,
    supports_ltp=True,
    supports_orderbook=True,
    supports_retry=True,
    supports_health_check=True,
    supports_rate_limit_awareness=True,
    supported_markets=[
        "GLOBAL",
    ],
    supported_assets=[
        "CRYPTO",
    ],
)