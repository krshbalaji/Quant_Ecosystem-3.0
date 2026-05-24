"""
Fyers portfolio adapter
"""

from quant_ecosystem.canonical.broker_models import (
    CanonicalPosition,
    CanonicalBalance,
)

from quant_ecosystem.portfolio.adapters.base_portfolio_adapter import BasePortfolioAdapter


class FyersPortfolioAdapter(BasePortfolioAdapter):

    def translate_positions(self, raw):
        out = []

        for row in raw or []:
            out.append(
                CanonicalPosition(
                    provider="fyers",
                    symbol=row.get("symbol", ""),
                    qty=row.get("qty", 0),
                    avg_price=row.get("avg_price", 0.0),
                    ltp=row.get("ltp", 0.0),
                    unrealized_pnl=row.get("unrealized_pnl", 0.0),
                    realized_pnl=row.get("realized_pnl", 0.0),
                    side=row.get("side", "BUY"),
                    product_type=row.get("productType", "CNC"),
                    raw_payload=row,
                )
            )

        return out

    def translate_balances(self, raw):
        return CanonicalBalance(
            provider="fyers",
            cash=raw.get("cash", 0.0),
            margin_available=raw.get("available_margin", 0.0),
            margin_used=raw.get("used_margin", 0.0),
            collateral=raw.get("collateral", 0.0),
            currency=raw.get("currency", "INR"),
            raw_payload=raw,
        )

    def translate_margin(self, raw):
        return {
            "available": raw.get("available_margin", 0.0),
            "used": raw.get("used_margin", 0.0),
        }

    def translate_portfolio_snapshot(self, raw):
        return {
            "positions": self.translate_positions(raw.get("positions", [])),
            "balance": self.translate_balances(raw.get("balance", {})),
        }