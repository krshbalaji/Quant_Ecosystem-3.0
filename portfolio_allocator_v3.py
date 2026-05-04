from config import Config
from firestore_client import get_positions, update_position
from risk_engine import allow_trade

class PortfolioAllocatorV3:

    def __init__(self):
        self.capital = getattr(Config, "CAPITAL", 100000)

    def allocate(self, signals, market_data):
        allocations = []

        portfolio = get_positions() or {}

        for signal in signals:
            symbol = signal["symbol"]
            side = signal["side"]
            strength = signal.get("strength", 0.5)

            if symbol not in market_data:
                continue

            md = market_data[symbol]
            price = md.get("price")

            if not price or price <= 0:
                continue

            qty = 0  # 🔥 ALWAYS initialize

            # =========================
            # EXISTING POSITION
            # =========================
            if symbol in portfolio:
                existing = portfolio[symbol]
                existing_qty = existing.get("qty", 0)
                existing_side = existing.get("side")

                # ---- SCALING
                if existing_side == side:
                    print(f"[ALLOCATOR] Scaling position: {symbol}")

                    # volatility-based scaling
                    high = md.get("high", price)
                    low = md.get("low", price)
                    volatility = abs(high - low) / price if price else 0.02

                    scale_factor = max(0.1, 0.3 - volatility)

                    qty = int(existing_qty * scale_factor)
                    qty = max(1, qty)

                # ---- REVERSAL
                else:
                    print(f"[ALLOCATOR] Reversing position: {symbol}")
                    qty = max(1, existing_qty * 2)

            # =========================
            # NEW POSITION
            # =========================
            else:
                if strength >= 1.5:
                    weight = 1.0
                elif strength >= 1.0:
                    weight = 0.7
                elif strength >= 0.5:
                    weight = 0.4
                else:
                    weight = 0.2

                capital = self.capital * weight

                high = md.get("high", price)
                low = md.get("low", price)
                volatility = abs(high - low) / price if price else 0.02
                volatility = max(volatility, 0.01)

                adjusted_price = price * (1 + volatility)

                qty = int(capital / adjusted_price)
                qty = max(1, qty)

                print(f"[ALLOCATOR] Trade: {symbol} {side} {qty}")

            # =========================
            # FINAL SAFETY CHECK
            # =========================
            if qty <= 0:
                continue

            # =========================
            # RISK ENGINE
            # =========================
            signal_check = {
                "symbol": symbol,
                "qty": qty,
                "strength": strength
            }

            if not allow_trade(signal_check, price):
                continue

            qty = signal_check["qty"]  # 🔥 IMPORTANT

            # =========================
            # UPDATE POSITION
            # =========================
            update_position(symbol, side, qty, price)

            allocations.append({
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "strength": strength,
                "capital_used": qty * price,
                "weight": 1.0
            })

        return allocations

        print(f"[VOL] {symbol} volatility={round(volatility,4)} qty={qty}")

    def calculate_volatility(md):
        price = md.get("price", 1)
        high = md.get("high", price)
        low = md.get("low", price)

        if price <= 0:
            return 0.02

        return abs(high - low) / price    