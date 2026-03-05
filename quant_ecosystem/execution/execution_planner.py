from __future__ import annotations

from typing import Dict, List


class ExecutionPlanner:
    """
    Converts target portfolio weights into broker-neutral order intents.
    """

    def __init__(self, portfolio_engine, state, market_data):
        self.portfolio_engine = portfolio_engine
        self.state = state
        self.market_data = market_data

    def plan_orders(self, target_portfolio: Dict[str, float]) -> List[Dict]:
        """
        Compute desired notional change per symbol and convert into qty orders.
        """
        if not target_portfolio:
            return []

        orders: List[Dict] = []
        latest_prices = getattr(self.state, "latest_prices", {}) or {}

        for symbol, target_weight in target_portfolio.items():
            price = latest_prices.get(symbol) or getattr(self.market_data, "get_latest_price", lambda s: None)(symbol)
            if price is None or price <= 0:
                continue

            equity = float(getattr(self.state, "equity", 0.0) or 0.0)
            if equity <= 0:
                continue

            target_notional = target_weight * equity
            current_pos = self.portfolio_engine.positions.get(symbol, {"net_qty": 0})
            current_notional = float(current_pos["net_qty"]) * float(price)
            delta_notional = target_notional - current_notional
            if abs(delta_notional) <= 0:
                continue

            qty = int(abs(delta_notional) / float(price))
            if qty <= 0:
                continue

            side = "BUY" if delta_notional > 0 else "SELL"

            orders.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "strategy_id": "multi_strategy_aggregator",
                }
            )

        return orders

