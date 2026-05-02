import math

class PortfolioAllocatorV2:
    def __init__(self, capital=100000, risk_per_trade=0.01):
        self.capital = capital
        self.risk_per_trade = risk_per_trade

    def allocate(self, signals, market_data):
        """
        signals = [{symbol, strength}]
        market_data = {symbol: {"price": x, "atr": y}}
        """

        total_strength = sum(s["strength"] for s in signals)

        allocations = []

        for signal in signals:
            symbol = signal["symbol"]
            strength = signal["strength"]

            if symbol not in market_data:
                continue

            price = market_data[symbol]["price"]
            atr = market_data[symbol]["atr"]

            if atr == 0:
                continue

            # 1. Weight allocation
            weight = strength / total_strength

            # 2. Capital allocation
            capital_alloc = self.capital * weight

            # 3. Risk per trade
            risk_amount = self.capital * self.risk_per_trade

            # 4. Position sizing (ATR based)
            qty = risk_amount / atr

            # 5. Adjust by capital
            max_qty_by_capital = capital_alloc / price
            final_qty = min(qty, max_qty_by_capital)

            allocations.append({
                "symbol": symbol,
                "qty": int(final_qty),
                "capital_used": round(final_qty * price, 2),
                "weight": round(weight, 2)
            })

        return allocations