"""
ViewTrade portfolio adapter
"""

from quant_ecosystem.canonical.broker_models import (
    CanonicalPosition,
    CanonicalBalance,
)

from quant_ecosystem.portfolio.adapters.base_portfolio_adapter import BasePortfolioAdapter


class ViewTradePortfolioAdapter(BasePortfolioAdapter):

    def translate_positions(self, raw):
        out = []

        for row in raw or []:
            out.append(
                CanonicalPosition(
                    provider="viewtrade",
                    symbol=row.get("ticker", ""),
                    qty=row.get("quantity", 0),
                    avg_price=row.get("avg_price", 0.0),
                    ltp=row.get("market_price", 0.0),
                    unrealized_pnl=row.get("upl", 0.0),
                    realized_pnl=row.get("rpl", 0.0),
                    side=row.get("side", "BUY"),
                    product_type="DELIVERY",
                    raw_payload=row,
                )
            )

        return out

    def translate_balances(self, raw):
        return CanonicalBalance(
            provider="viewtrade",
            cash=raw.get("cash", 0.0),
            margin_available=raw.get("buying_power", 0.0),
            margin_used=raw.get("margin_used", 0.0),
            collateral=0.0,
            currency=raw.get("currency", "USD"),
            raw_payload=raw,
        )

    def translate_margin(self, raw):
        return raw

    def translate_portfolio_snapshot(self, raw):
        return {
            "positions": self.translate_positions(raw.get("positions", [])),
            "balance": self.translate_balances(raw.get("balance", {})),
        }