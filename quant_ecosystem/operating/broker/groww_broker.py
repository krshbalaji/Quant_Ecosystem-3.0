from __future__ import annotations

from datetime import datetime

from quant_ecosystem.operating.core.config_loader import Config
from quant_ecosystem.research.utils.decimal_utils import quantize


class GrowwBroker:
    """Groww broker with resilient simulated fallback."""

    def __init__(self, config=None, **kwargs):
        cfg = config or Config()
        self.api_key = (getattr(cfg, "groww_api_key", "") or "").strip()
        self.api_secret = (getattr(cfg, "groww_api_secret", "") or "").strip()
        self.enable_live = bool(getattr(cfg, "groww_enable_live", False))
        self.connected = False
        self.account_source = "SIMULATED"

        self.cash_balance = quantize(float(getattr(cfg, "capital", 100000.0) or 100000.0), 4)
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.positions = {}
        self.orders = []
        self.tradebook = []

    def connect(self):
        if self.enable_live and self.api_key and self.api_secret:
            self.account_source = "GROWW_LIVE"
        self.connected = True

    def is_connected(self):
        mode = str(getattr(Config(), "mode", "PAPER") or "PAPER").upper()
        if mode == "PAPER" or self.account_source == "SIMULATED":
            return True
        return bool(self.connected and self.account_source == "GROWW_LIVE")

    def place_order(self, symbol, side, qty, price=None, fee=0.0, meta=None, **kwargs):
        if not self.connected:
            raise RuntimeError("Broker not connected")
        if price is None:
            raise ValueError("price is required")

        side = str(side).upper().strip()
        qty = int(qty)
        price = quantize(float(price), 4)
        fee = quantize(float(fee or 0.0), 4)
        realized_pnl = self._apply_fill(symbol=symbol, side=side, qty=qty, price=price, fee=fee)
        order = {
            "id": len(self.orders) + 1,
            "order_id": f"GROWW-{len(self.orders) + 1:06d}",
            "ts": datetime.now().isoformat(timespec="seconds"),
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "fee": fee,
            "status": "FILLED",
            "realized_pnl": quantize(realized_pnl, 4),
            "account_source": self.account_source,
            "meta": meta or {},
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
        return self.place_order(symbol=symbol, side=side, qty=abs(net_qty), price=kwargs.get("price", pos.get("avg_price", 0.0)), fee=kwargs.get("fee", 0.0), meta={"close": True})

    def get_positions(self):
        return [
            {"symbol": symbol, "net_qty": int(pos["net_qty"]), "avg_price": quantize(float(pos["avg_price"]), 4)}
            for symbol, pos in self.positions.items()
        ]

    def get_orders(self):
        return [row.copy() for row in self.orders]

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
        return {
            "cash_balance": quantize(self.cash_balance, 4),
            "realized_pnl": quantize(self.realized_pnl, 4),
            "unrealized_pnl": quantize(unrealized, 4),
            "fees_paid": quantize(self.fees_paid, 4),
            "equity": quantize(self.cash_balance + market_value, 4),
            "orders": self.get_orders(),
            "tradebook": [row.copy() for row in self.tradebook],
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
            self.positions[symbol] = {"net_qty": new_qty, "avg_price": quantize(weighted_cost / total_qty, 4)}
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
