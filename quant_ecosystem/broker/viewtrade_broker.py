from datetime import datetime

from quant_ecosystem.broker.adapters.coinswitch_adapter import CoinSwitchAdapter
from quant_ecosystem.core.config_loader import Config
from quant_ecosystem.utils.decimal_utils import quantize


class CoinSwitchBroker:
    """CoinSwitch broker with safe simulated fallback.

    The class mirrors the existing broker interface used by BrokerRouter.
    """

    def __init__(self, **kwargs):
        cfg = Config()
        self.api_key = (cfg.coinswitch_api_key or "").strip()
        self.api_secret = (cfg.coinswitch_api_secret or "").strip()
        self.base_url = (cfg.coinswitch_base_url or "").strip()
        self.enable_live = bool(cfg.coinswitch_enable_live)

        self.connected = False
        self.live_client = CoinSwitchAdapter(self.api_key, self.api_secret, self.base_url)
        self.account_source = "SIMULATED"

        self.cash_balance = quantize(100000.0, 4)
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.positions = {}
        self.orders = []
        self.tradebook = []

        self.order_path = "/trade/api/v2/order"
        self.balance_path = "/trade/api/v2/user/balance"
        self.orders_path = "/trade/api/v2/orders"
        self.positions_path = "/trade/api/v2/positions"

    def connect(self):
        if self.enable_live and self.live_client.is_ready():
            probe = self.live_client.get(self.balance_path)
            if probe.get("ok"):
                self.account_source = "COINSWITCH_LIVE"
                self.connected = True
                print("Broker Connected : CoinSwitch (live)")
                return
            print(f"CoinSwitch live probe failed: {probe.get('error', 'unknown')}. Using simulated broker.")
        else:
            if self.enable_live:
                print("CoinSwitch live disabled due to missing API config. Using simulated broker.")

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
            raise ValueError("price is required")
        price = quantize(float(price), 4)
        fee = quantize(float(fee or 0.0), 4)
        meta = meta or {}

        exchange_symbol = self._normalize_symbol(symbol)

        if self.account_source == "COINSWITCH_LIVE":
            payload = {
                "symbol": exchange_symbol,
                "side": side,
                "order_type": "MARKET",
                "quantity": qty,
            }
            live = self.live_client.post(self.order_path, payload)
            if not live.get("ok"):
                print(f"CoinSwitch live order failed: {live.get('error', 'unknown')}. Falling back to simulated fill.")
            else:
                order = self._record_order(symbol, side, qty, price, fee, 0.0, meta, status="SUBMITTED")
                return order

        realized_pnl = self._apply_fill(symbol=symbol, side=side, qty=qty, price=price, fee=fee)
        order = self._record_order(symbol, side, qty, price, fee, realized_pnl, meta, status="FILLED")
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
        if self.account_source == "COINSWITCH_LIVE":
            data = self.live_client.get(self.balance_path)
            if data.get("ok"):
                return quantize(self._extract_balance(data.get("data", {})), 4)
        return quantize(self.cash_balance, 4)

    def get_orders(self):
        if self.account_source == "COINSWITCH_LIVE":
            data = self.live_client.get(self.orders_path)
            if data.get("ok"):
                return self._parse_live_orders(data.get("data", {}))
        return [item.copy() for item in self.orders]

    def get_positions(self):
        if self.account_source == "COINSWITCH_LIVE":
            data = self.live_client.get(self.positions_path)
            if data.get("ok"):
                return self._parse_live_positions(data.get("data", {}))
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

        if self.account_source == "COINSWITCH_LIVE":
            positions = self.get_positions()
            orders = self.get_orders()
            cash = self.get_balance()
            unrealized = 0.0
            market_value = 0.0
            for row in positions:
                symbol = row.get("symbol")
                qty = float(row.get("net_qty", 0.0))
                avg = float(row.get("avg_price", 0.0))
                px = float(latest_prices.get(symbol, avg))
                unrealized += (px - avg) * qty
                market_value += qty * px
            equity = quantize(cash + market_value, 4)
            return {
                "cash_balance": quantize(cash, 4),
                "realized_pnl": quantize(self.realized_pnl, 4),
                "unrealized_pnl": quantize(unrealized, 4),
                "fees_paid": quantize(self.fees_paid, 4),
                "equity": equity,
                "orders": orders,
                "tradebook": [item.copy() for item in self.tradebook],
                "positions": positions,
                "account_source": self.account_source,
            }

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

    def _record_order(self, symbol, side, qty, price, fee, realized_pnl, meta, status):
        order = {
            "id": len(self.orders) + 1,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": quantize(price, 4),
            "fee": quantize(fee, 4),
            "status": status,
            "realized_pnl": quantize(realized_pnl, 4),
            "meta": meta or {},
        }
        self.orders.append(order)
        self.tradebook.append(order.copy())
        return order

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

    def _normalize_symbol(self, symbol):
        sym = str(symbol).upper().strip()
        if sym.startswith("CRYPTO:"):
            base = sym.split(":", 1)[1]
            if base.endswith("USDT") and len(base) > 4:
                return f"{base[:-4]}/USDT"
            if base.endswith("INR") and len(base) > 3:
                return f"{base[:-3]}/INR"
            return base
        return sym

    def _extract_balance(self, payload):
        if isinstance(payload, dict):
            for key in ("cash", "available_balance", "balance", "inr_balance"):
                value = payload.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return float(self.cash_balance)

    def _parse_live_orders(self, payload):
        rows = payload.get("orders") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return [item.copy() for item in self.orders]
        out = []
        for idx, item in enumerate(rows, start=1):
            out.append(
                {
                    "id": item.get("id", idx),
                    "ts": item.get("timestamp", ""),
                    "symbol": str(item.get("symbol", "")),
                    "side": str(item.get("side", "")).upper(),
                    "qty": int(float(item.get("qty", item.get("quantity", 0)) or 0)),
                    "price": quantize(float(item.get("price", 0.0) or 0.0), 4),
                    "fee": quantize(float(item.get("fee", 0.0) or 0.0), 4),
                    "status": str(item.get("status", "UNKNOWN")),
                    "realized_pnl": quantize(float(item.get("realized_pnl", 0.0) or 0.0), 4),
                    "meta": item.get("meta", {}),
                }
            )
        return out

    def _parse_live_positions(self, payload):
        rows = payload.get("positions") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return self.get_positions()
        out = []
        for item in rows:
            out.append(
                {
                    "symbol": str(item.get("symbol", "")),
                    "net_qty": int(float(item.get("net_qty", item.get("qty", 0)) or 0)),
                    "avg_price": quantize(float(item.get("avg_price", item.get("price", 0.0)) or 0.0), 4),
                }
            )
        return out
