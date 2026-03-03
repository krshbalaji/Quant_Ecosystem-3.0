from datetime import datetime
import os

from config.env_loader import Env
from utils.decimal_utils import quantize


class FyersBroker:

    def __init__(self):
        self.client_id = (Env.FYERS_CLIENT_ID or "").strip()
        self.secret = (Env.FYERS_SECRET_KEY or "").strip()
        self.access_token = (os.getenv("FYERS_ACCESS_TOKEN", "") or "").strip()

        self.connected = False
        self.live_client = None
        self.account_source = "SIMULATED"

        self.cash_balance = quantize(Env.CAPITAL, 4)
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.positions = {}
        self.orders = []
        self.tradebook = []

    def connect(self):
        # Keep startup resilient: if live API is not ready, continue in simulated mode.
        if not self.client_id:
            print("⚠ FYERS API not configured. Using simulated broker.")
            self.connected = True
            return

        try:
            from broker.adapters.fyers_adapter import FyersAdapter

            if self.access_token:
                adapter = FyersAdapter(app_id=self.client_id, access_token=self.access_token)
                adapter.login()
                self.live_client = adapter
                self.account_source = "FYERS_LIVE"
                print("Broker Connected : Fyers (live)")
            else:
                print("⚠ FYERS access token missing. Using simulated broker.")
        except Exception as exc:
            print(f"⚠ FYERS live init failed ({exc}). Using simulated broker.")

        self.connected = True

    def place_order(self, symbol, side, qty, price=None, fee=0.0, meta=None, **kwargs):
        if not self.connected:
            raise RuntimeError("Broker not connected")

        side = str(side).upper().strip()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        qty = int(qty)
        if qty <= 0:
            raise ValueError("qty must be > 0")

        if price is None:
            raise ValueError("price is required for simulated execution")
        price = quantize(float(price), 4)
        fee = quantize(float(fee or 0.0), 4)
        meta = meta or {}

        realized_pnl = self._apply_fill(symbol=symbol, side=side, qty=qty, price=price, fee=fee)
        order = {
            "id": len(self.orders) + 1,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "fee": fee,
            "status": "FILLED",
            "realized_pnl": quantize(realized_pnl, 4),
            "meta": meta,
        }
        self.orders.append(order)
        self.tradebook.append(order.copy())

        return order

    def close_position(self, symbol, **kwargs):
        pos = self.positions.get(symbol)
        if not pos:
            return {"status": "NO_POSITION", "symbol": symbol}

        net_qty = int(pos.get("net_qty", 0))
        if net_qty == 0:
            return {"status": "NO_POSITION", "symbol": symbol}

        side = "SELL" if net_qty > 0 else "BUY"
        qty = abs(net_qty)
        price = kwargs.get("price", pos.get("avg_price", 0.0))
        fee = kwargs.get("fee", 0.0)
        return self.place_order(symbol=symbol, side=side, qty=qty, price=price, fee=fee, meta={"close": True})

    def get_balance(self):
        return quantize(self.cash_balance, 4)

    def get_orders(self):
        return [item.copy() for item in self.orders]

    def get_positions(self):
        rows = []
        for symbol, pos in self.positions.items():
            rows.append(
                {
                    "symbol": symbol,
                    "net_qty": int(pos["net_qty"]),
                    "avg_price": quantize(float(pos["avg_price"]), 4),
                }
            )
        return rows

    def get_account_snapshot(self, latest_prices=None):
        latest_prices = latest_prices or {}
        unrealized = 0.0
        market_value = 0.0

        for symbol, pos in self.positions.items():
            qty = int(pos.get("net_qty", 0))
            avg = float(pos.get("avg_price", 0.0))
            px = float(latest_prices.get(symbol, avg))
            unrealized += (px - avg) * qty
            market_value += qty * px

        unrealized = quantize(unrealized, 4)
        equity = quantize(self.cash_balance + market_value, 4)

        return {
            "cash_balance": quantize(self.cash_balance, 4),
            "realized_pnl": quantize(self.realized_pnl, 4),
            "unrealized_pnl": unrealized,
            "fees_paid": quantize(self.fees_paid, 4),
            "equity": equity,
            "orders": self.get_orders(),
            "tradebook": [item.copy() for item in self.tradebook],
            "positions": self.get_positions(),
            "account_source": self.account_source,
        }

    def _apply_fill(self, symbol, side, qty, price, fee):
        current = self.positions.get(symbol, {"net_qty": 0, "avg_price": 0.0})
        current_qty = int(current["net_qty"])
        current_avg = float(current["avg_price"])

        signed_fill = qty if side == "BUY" else -qty
        new_qty = current_qty + signed_fill

        if side == "BUY":
            self.cash_balance = quantize(self.cash_balance - ((price * qty) + fee), 4)
        else:
            self.cash_balance = quantize(self.cash_balance + ((price * qty) - fee), 4)

        self.fees_paid = quantize(self.fees_paid + fee, 4)

        realized_pnl = 0.0
        if current_qty == 0:
            self.positions[symbol] = {"net_qty": new_qty, "avg_price": price}
            return realized_pnl

        same_direction = (current_qty > 0 and signed_fill > 0) or (current_qty < 0 and signed_fill < 0)
        if same_direction:
            total_qty = abs(current_qty) + abs(signed_fill)
            weighted_cost = (abs(current_qty) * current_avg) + (abs(signed_fill) * price)
            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": quantize(weighted_cost / total_qty, 4),
            }
            return realized_pnl

        closing_qty = min(abs(current_qty), abs(signed_fill))
        direction = 1 if current_qty > 0 else -1
        realized_pnl = quantize(closing_qty * (price - current_avg) * direction, 4)
        self.realized_pnl = quantize(self.realized_pnl + realized_pnl, 4)

        if new_qty == 0:
            self.positions.pop(symbol, None)
        elif (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0):
            self.positions[symbol] = {"net_qty": new_qty, "avg_price": quantize(current_avg, 4)}
        else:
            self.positions[symbol] = {"net_qty": new_qty, "avg_price": price}

        return realized_pnl
