import math
import time
import json
import os


class PortfolioAllocatorV3:
    def __init__(self, capital=100000, risk_per_trade=0.01):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.file = "portfolio_state.json"
        self.positions = self._load_positions()

    def _load_positions(self):
        if os.path.exists(self.file):
            with open(self.file, "r") as f:
                return json.load(f)
        return {}

    def _save_positions(self):
        with open(self.file, "w") as f:
            json.dump(self.positions, f, indent=2)

    def allocate(self, signals, market_data):
        if not signals:
            return []

        total_strength = sum(s.get("strength", 0) for s in signals)

        allocations = []

        for signal in signals:
            symbol = signal.get("symbol")
            side = signal.get("side")
            strength = signal.get("strength", 0)

            if not symbol or not side:
                continue

            if symbol not in market_data:
                continue

            # ---- duplicate protection ----
            if symbol in self.positions:
                existing = self.positions[symbol]
                if existing["side"] == side:
                    print(f"[ALLOCATOR] Skipping duplicate: {symbol}")
                    continue

            price = market_data[symbol]["price"]
            atr = market_data[symbol]["atr"]

            if atr == 0 or price == 0:
                continue

            weight = strength / total_strength if total_strength else 0

            capital_alloc = self.capital * weight
            risk_amount = self.capital * self.risk_per_trade

            qty_by_risk = risk_amount / atr
            max_qty_by_capital = capital_alloc / price

            final_qty = int(min(qty_by_risk, max_qty_by_capital))

            if final_qty <= 0:
                continue

            trade = {
                "symbol": symbol,
                "side": side,
                "qty": final_qty,
                "strength": strength,
                "capital_used": round(final_qty * price, 2),
                "weight": round(weight, 2)
            }

            # ---- store ----
            self.positions[symbol] = {
                "side": side,
                "qty": final_qty,
                "timestamp": time.time()
            }

            self._save_positions()

            print(f"[ALLOCATOR] Trade: {trade}")

            allocations.append(trade)

        return allocations