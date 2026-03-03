from broker.adapters.fyers_adapter import FyersAdapter
from core.config_loader import Config
from utils.decimal_utils import quantize


class FyersBroker:

    def __init__(self):
        self.config = Config()
        self.connected = False
        self.adapter = None
        self._paper_positions = {}
        self._paper_orders = []
        self._paper_tradebook = []
        self._paper_cash = 100000.0
        self._paper_fees = 0.0
        self._paper_realized = 0.0

    def connect(self):
        print("Connecting to Fyers...")

        if not self.config.fyers_token:
            if self.config.mode == "PAPER":
                self.connected = True
                print("Fyers token missing; PAPER mode connection enabled")
                return
            raise Exception("Missing FYERS_ACCESS_TOKEN in .env")

        self.adapter = FyersAdapter(
            app_id=self.config.fyers_app_id,
            access_token=self.config.fyers_token,
        )
        self.adapter.login()
        self.connected = True
        print("Fyers Connected Successfully")

    def place_order(self, symbol, side, qty, price=None, fee=0.0, meta=None):
        if not self.connected:
            raise Exception("Broker not connected")

        if self.config.mode == "PAPER":
            print(f"Placing order via Fyers API | {side} {symbol} {qty}")
            fill_price = quantize(float(price or 0.0), 4)
            fee_q = quantize(float(fee or 0.0), 4)
            fill_meta = self._paper_apply_fill(symbol=symbol, side=side, qty=int(qty), price=fill_price)
            realized = float(fill_meta.get("realized_pnl", 0.0))
            notional = fill_price * int(qty)
            if side == "BUY":
                self._paper_cash -= notional + fee_q
            else:
                self._paper_cash += notional - fee_q
            self._paper_cash = quantize(self._paper_cash, 4)
            self._paper_fees = quantize(self._paper_fees + fee_q, 4)
            self._paper_realized = quantize(self._paper_realized + realized, 4)
            order = {
                "order_id": f"PAPER_{len(self._paper_orders)+1}",
                "symbol": symbol,
                "side": side,
                "qty": int(qty),
                "price": fill_price,
                "fee": fee_q,
                "status": "FILLED",
                "realized_pnl": quantize(realized, 4),
                "closing_qty": int(fill_meta.get("closing_qty", 0)),
                "opening_qty": int(fill_meta.get("opening_qty", 0)),
                "meta": meta or {},
            }
            self._paper_orders.append(order)
            self._paper_tradebook.append(
                {
                    "symbol": symbol,
                    "qty": int(qty),
                    "price": fill_price,
                    "fee": fee_q,
                    "side": side,
                }
            )
            return {
                **order
            }

        raw = self.adapter.place_order(symbol=symbol, side=side, qty=qty)
        order_id = raw.get("id") or raw.get("order_id") or raw.get("s") or "UNKNOWN"
        return {
            "order_id": str(order_id),
            "symbol": symbol,
            "side": side,
            "qty": int(qty),
            "price": quantize(float(price or 0.0), 4),
            "fee": quantize(float(fee or 0.0), 4),
            "status": "FILLED" if raw.get("s") in {"ok", "success", "OK"} else "SENT",
            "realized_pnl": 0.0,
            "meta": meta or {},
            "raw": raw,
        }

    def close_position(self, symbol):
        if not self.connected:
            raise Exception("Broker not connected")
        return {"symbol": symbol, "status": "CLOSED"}

    def get_balance(self):
        if not self.connected:
            raise Exception("Broker not connected")

        if self.config.mode == "PAPER":
            return {"status": "OK", "available_balance": quantize(self._paper_cash, 4)}

        funds = self.adapter.get_funds()
        available = self._extract_available_balance(funds)
        return {"status": "OK", "available_balance": quantize(available, 2), "raw": funds}

    def get_orders(self):
        if self.config.mode == "PAPER":
            return list(self._paper_orders)
        data = self.adapter.get_orderbook()
        return self._normalize_orderbook(data)

    def get_positions(self):
        if self.config.mode == "PAPER":
            out = []
            for symbol, pos in self._paper_positions.items():
                out.append(
                    {
                        "symbol": symbol,
                        "net_qty": int(pos["net_qty"]),
                        "avg_price": quantize(pos["avg_price"], 4),
                        "realized_pnl": 0.0,
                        "unrealized_pnl": 0.0,
                    }
                )
            return out
        data = self.adapter.get_positions()
        return self._normalize_positions(data)

    def get_tradebook(self):
        if self.config.mode == "PAPER":
            return list(self._paper_tradebook)
        data = self.adapter.get_tradebook()
        return self._normalize_tradebook(data)

    def get_account_snapshot(self, latest_prices=None):
        latest_prices = latest_prices or {}

        if self.config.mode == "PAPER":
            positions = self.get_positions()
            unrealized = 0.0
            market_value = 0.0
            for pos in positions:
                symbol = pos["symbol"]
                px = float(latest_prices.get(symbol, pos["avg_price"]))
                unrealized += (px - pos["avg_price"]) * pos["net_qty"]
                market_value += px * pos["net_qty"]
            equity = self._paper_cash + market_value
            return {
                "cash_balance": quantize(self._paper_cash, 4),
                "realized_pnl": quantize(self._paper_realized, 4),
                "unrealized_pnl": quantize(unrealized, 4),
                "fees_paid": quantize(self._paper_fees, 4),
                "equity": quantize(equity, 4),
                "positions": positions,
                "orders": list(self._paper_orders),
                "tradebook": list(self._paper_tradebook),
                "account_source": "PAPER_LEDGER",
            }

        funds = self.adapter.get_funds()
        positions_raw = self.adapter.get_positions()
        orders_raw = self.adapter.get_orderbook()
        trades_raw = self.adapter.get_tradebook()

        positions = self._normalize_positions(positions_raw)
        orders = self._normalize_orderbook(orders_raw)
        tradebook = self._normalize_tradebook(trades_raw)

        cash = self._extract_available_balance(funds)
        realized = sum(float(item.get("realized_pnl", 0.0)) for item in positions)
        unrealized = sum(float(item.get("unrealized_pnl", 0.0)) for item in positions)
        fees = sum(float(item.get("fee", 0.0)) for item in tradebook)

        market_value = 0.0
        for pos in positions:
            symbol = pos["symbol"]
            px = float(latest_prices.get(symbol, pos["avg_price"]))
            market_value += px * float(pos["net_qty"])

        equity = cash + market_value
        return {
            "cash_balance": quantize(cash, 4),
            "realized_pnl": quantize(realized, 4),
            "unrealized_pnl": quantize(unrealized, 4),
            "fees_paid": quantize(fees, 4),
            "equity": quantize(equity, 4),
            "positions": positions,
            "orders": orders,
            "tradebook": tradebook,
            "account_source": "BROKER_API",
        }

    def _normalize_positions(self, payload):
        rows = payload.get("netPositions", payload.get("positions", [])) if isinstance(payload, dict) else []
        out = []
        for row in rows:
            symbol = row.get("symbol") or row.get("sym") or ""
            qty = float(row.get("netQty", row.get("qty", row.get("netqty", 0))))
            avg = float(row.get("buyAvg", row.get("avgPrice", row.get("avg", 0.0))))
            realized = float(row.get("realized_profit", row.get("realized", 0.0)))
            unrealized = float(row.get("pl", row.get("unrealized", 0.0)))
            out.append(
                {
                    "symbol": symbol,
                    "net_qty": int(qty),
                    "avg_price": quantize(avg, 4),
                    "realized_pnl": quantize(realized, 4),
                    "unrealized_pnl": quantize(unrealized, 4),
                }
            )
        return out

    def _normalize_orderbook(self, payload):
        rows = payload.get("orderBook", payload.get("orders", [])) if isinstance(payload, dict) else []
        out = []
        for row in rows:
            out.append(
                {
                    "order_id": str(row.get("id", row.get("orderNumStatus", ""))),
                    "symbol": row.get("symbol", ""),
                    "side": "BUY" if str(row.get("side", "1")) in {"1", "BUY"} else "SELL",
                    "qty": int(float(row.get("qty", 0))),
                    "price": quantize(float(row.get("tradedPrice", row.get("limitPrice", 0.0))), 4),
                    "status": str(row.get("status", row.get("orderStatus", ""))),
                }
            )
        return out

    def _normalize_tradebook(self, payload):
        rows = payload.get("tradeBook", payload.get("trades", [])) if isinstance(payload, dict) else []
        out = []
        for row in rows:
            out.append(
                {
                    "symbol": row.get("symbol", ""),
                    "qty": int(float(row.get("tradedQty", row.get("qty", 0)))),
                    "price": quantize(float(row.get("tradedPrice", row.get("price", 0.0))), 4),
                    "fee": quantize(float(row.get("charges", row.get("fee", 0.0))), 4),
                    "side": "BUY" if str(row.get("side", "1")) in {"1", "BUY"} else "SELL",
                }
            )
        return out

    def _extract_available_balance(self, funds_payload):
        if not isinstance(funds_payload, dict):
            return 0.0
        fund_limit = funds_payload.get("fund_limit", [])
        for row in fund_limit:
            if str(row.get("title", "")).lower().startswith("available"):
                return float(row.get("equityAmount", 0.0))
        return float(funds_payload.get("available_balance", 0.0))

    def _paper_apply_fill(self, symbol, side, qty, price):
        current = self._paper_positions.get(symbol, {"net_qty": 0, "avg_price": 0.0})
        current_qty = int(current["net_qty"])
        current_avg = float(current["avg_price"])
        signed_fill = qty if side == "BUY" else -qty
        new_qty = current_qty + signed_fill
        realized = 0.0
        closing_qty = 0
        opening_qty = 0

        if current_qty == 0:
            self._paper_positions[symbol] = {"net_qty": new_qty, "avg_price": price}
            return {
                "realized_pnl": 0.0,
                "closing_qty": 0,
                "opening_qty": abs(signed_fill),
                "prev_qty": current_qty,
                "new_qty": new_qty,
            }

        same_dir = (current_qty > 0 and signed_fill > 0) or (current_qty < 0 and signed_fill < 0)
        if same_dir:
            total_qty = abs(current_qty) + abs(signed_fill)
            weighted = (abs(current_qty) * current_avg) + (abs(signed_fill) * price)
            self._paper_positions[symbol] = {"net_qty": new_qty, "avg_price": quantize(weighted / total_qty, 4)}
            return {
                "realized_pnl": 0.0,
                "closing_qty": 0,
                "opening_qty": abs(signed_fill),
                "prev_qty": current_qty,
                "new_qty": new_qty,
            }

        closing_qty = min(abs(current_qty), abs(signed_fill))
        direction = 1 if current_qty > 0 else -1
        realized = closing_qty * (price - current_avg) * direction

        if new_qty == 0:
            self._paper_positions.pop(symbol, None)
        elif (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0):
            self._paper_positions[symbol] = {"net_qty": new_qty, "avg_price": quantize(current_avg, 4)}
        else:
            self._paper_positions[symbol] = {"net_qty": new_qty, "avg_price": price}
            opening_qty = abs(new_qty)

        return {
            "realized_pnl": realized,
            "closing_qty": int(closing_qty),
            "opening_qty": int(opening_qty),
            "prev_qty": current_qty,
            "new_qty": new_qty,
        }
