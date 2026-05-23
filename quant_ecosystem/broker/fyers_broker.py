from datetime import datetime
import os
from typing import Any, Dict, List, Optional

from config.env_loader import Env
from quant_ecosystem.utils.decimal_utils import quantize
from quant_ecosystem.broker.fyers_token_manager import FyersTokenManager
from quant_ecosystem.notifications.telegram_notifier import TelegramNotifier

from quant_ecosystem.broker.base_broker import BaseBroker
from quant_ecosystem.broker.broker_capabilities import FYERS_CAPABILITIES


class FyersBroker(BaseBroker):
    """
    Production FYERS broker.

    Preserves existing QE3 behavior:
    - live auth
    - auto token refresh
    - telegram auth alert
    - simulated fallback
    - account snapshot support

    Adds Pack17:
    - capability contract
    - reconciliation support
    - health check
    - canonical broker interface
    """

    capabilities = FYERS_CAPABILITIES

    def __init__(self, config=None, **kwargs):
        self._config = config

        self.client_id = (Env.FYERS_CLIENT_ID or "").strip()
        self.secret = (Env.FYERS_SECRET_KEY or "").strip()
        self.access_token = (
            os.getenv("FYERS_ACCESS_TOKEN", "") or ""
        ).strip()

        self.connected = False
        self.live_client = None
        self.account_source = "SIMULATED"

        self.cash_balance = quantize(Env.CAPITAL, 4)
        self.realized_pnl = 0.0
        self.fees_paid = 0.0

        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []
        self.tradebook: List[Dict[str, Any]] = []

    # =========================================================
    # CONNECTION
    # =========================================================

    def connect(self):
        if not self.client_id:
            print("FYERS API not configured. Using simulated broker.")
            self.connected = True
            self.account_source = "SIMULATED"
            return

        from quant_ecosystem.broker.adapters.fyers_adapter import FyersAdapter

        def try_live_connect():
            fresh_token = (
                os.getenv("FYERS_ACCESS_TOKEN", "") or ""
            ).strip()

            if not fresh_token:
                raise RuntimeError(
                    "FYERS access token missing"
                )

            adapter = FyersAdapter(
                app_id=self.client_id,
                access_token=fresh_token,
            )

            adapter.login()

            auth_probe = adapter.get_funds()

            if (
                isinstance(auth_probe, dict)
                and auth_probe.get("code") == -16
            ):
                raise RuntimeError(
                    "FYERS authentication failed: "
                    "access token invalid/expired"
                )

            self.live_client = adapter
            self.connected = True
            self.account_source = "FYERS_LIVE"

            print("Broker Connected : Fyers (live)")

        try:
            try_live_connect()
            return

        except Exception as exc:
            print(f"FYERS auth failed: {exc}")
            print("Attempting automatic token refresh...")

            try:
                mgr = FyersTokenManager()
                mgr.generate_token()

                try_live_connect()

                print(
                    "FYERS live reconnected after token refresh."
                )
                return

            except Exception as refresh_err:
                print(
                    f"Token refresh failed: {refresh_err}"
                )

                try:
                    TelegramNotifier().send(
                        f"⚠️ *QE3 FYERS AUTH FAILURE*\n"
                        f"{refresh_err}"
                    )
                except Exception:
                    pass

        print("Falling back to simulated broker.")

        self.connected = True
        self.live_client = None
        self.account_source = "SIMULATED"

    # =========================================================
    # EXECUTION
    # =========================================================

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float = None,
        fee: float = 0.0,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError("Broker not connected")

        if self.live_client:
            return self.live_client.place_order(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                fee=fee,
                meta=meta or {},
            )

        side = str(side).upper().strip()

        if side not in {"BUY", "SELL"}:
            raise ValueError(
                "side must be BUY or SELL"
            )

        qty = int(qty)

        if qty <= 0:
            raise ValueError(
                "qty must be > 0"
            )

        if price is None:
            raise ValueError(
                "price required for simulated execution"
            )

        price = quantize(float(price), 4)
        fee = quantize(float(fee or 0.0), 4)
        meta = meta or {}

        realized_pnl = self._apply_fill(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            fee=fee,
        )

        order = {
            "id": str(len(self.orders) + 1),
            "ts": datetime.now().isoformat(
                timespec="seconds"
            ),
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "fee": fee,
            "status": "FILLED",
            "filledQty": qty,
            "remainingQuantity": 0,
            "tradedPrice": price,
            "realized_pnl": quantize(realized_pnl, 4),
            "meta": meta,
        }

        self.orders.append(order)
        self.tradebook.append(order.copy())

        return order

    def cancel_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:

        if not self.live_client:
            raise RuntimeError(
                "cancel_order unavailable in simulation"
            )

        return self.live_client.cancel_order(order_id)

    def modify_order(
        self,
        order_id: str,
        qty: int = None,
        price: float = None,
    ) -> Dict[str, Any]:

        if not self.live_client:
            raise RuntimeError(
                "modify_order unavailable in simulation"
            )

        return self.live_client.modify_order(
            order_id=order_id,
            qty=qty,
            price=price,
        )

    # =========================================================
    # RECONCILIATION
    # =========================================================

    def get_order_status(
        self,
        order_id: str
    ) -> Dict[str, Any]:

        if self.live_client:
            return self.live_client.get_order_status(
                order_id
            )

        for order in self.orders:
            if str(order.get("id")) == str(order_id):
                return order.copy()

        raise RuntimeError(
            f"Order not found: {order_id}"
        )

    def get_order_history(self) -> List[Dict[str, Any]]:
        if self.live_client:
            return self.live_client.get_orders()

        return [o.copy() for o in self.orders]

    # =========================================================
    # ACCOUNT
    # =========================================================

    def get_balance(self):
        if self.live_client:
            try:
                return self.live_client.get_funds()
            except Exception:
                pass

        return quantize(self.cash_balance, 4)

    def get_positions(self):
        if self.live_client:
            try:
                return self.live_client.get_positions()
            except Exception as exc:
                print(
                    f"LIVE POSITIONS FAILED: {exc}"
                )

        rows = []

        for symbol, pos in self.positions.items():
            rows.append(
                {
                    "symbol": symbol,
                    "net_qty": int(pos["net_qty"]),
                    "avg_price": quantize(
                        float(pos["avg_price"]),
                        4,
                    ),
                }
            )

        return rows

    def get_holdings(self):
        if self.live_client:
            try:
                return self.live_client.get_holdings()
            except Exception:
                return []

        return []

    def get_account_snapshot(
        self,
        latest_prices=None
    ):

        if self.live_client:
            try:
                return self.live_client.get_account_snapshot()
            except Exception as exc:
                print(
                    f"LIVE SNAPSHOT FAILED: {exc}"
                )

        latest_prices = latest_prices or {}

        unrealized = 0.0
        market_value = 0.0

        for symbol, pos in self.positions.items():
            qty = int(pos.get("net_qty", 0))
            avg = float(pos.get("avg_price", 0.0))
            px = float(
                latest_prices.get(symbol, avg)
            )

            unrealized += (px - avg) * qty
            market_value += qty * px

        unrealized = quantize(unrealized, 4)
        equity = quantize(
            self.cash_balance + market_value,
            4,
        )

        return {
            "cash_balance": quantize(
                self.cash_balance,
                4,
            ),
            "realized_pnl": quantize(
                self.realized_pnl,
                4,
            ),
            "unrealized_pnl": unrealized,
            "fees_paid": quantize(
                self.fees_paid,
                4,
            ),
            "equity": equity,
            "orders": self.get_order_history(),
            "tradebook": [
                item.copy()
                for item in self.tradebook
            ],
            "positions": self.get_positions(),
            "account_source": self.account_source,
        }

    # =========================================================
    # HEALTH
    # =========================================================

    def health_check(self):

        if not self.connected:
            return {
                "broker": "fyers",
                "healthy": False,
                "details": "not connected",
            }

        if self.account_source == "SIMULATED":
            return {
                "broker": "fyers",
                "healthy": True,
                "details": "simulation mode",
            }

        try:
            self.live_client.get_funds()

            return {
                "broker": "fyers",
                "healthy": True,
                "details": "live healthy",
            }

        except Exception as exc:
            return {
                "broker": "fyers",
                "healthy": False,
                "details": str(exc),
            }

    # =========================================================
    # POSITION MANAGEMENT
    # =========================================================

    def close_position(
        self,
        symbol,
        **kwargs
    ):

        pos = self.positions.get(symbol)

        if not pos:
            return {
                "status": "NO_POSITION",
                "symbol": symbol,
            }

        net_qty = int(
            pos.get("net_qty", 0)
        )

        if net_qty == 0:
            return {
                "status": "NO_POSITION",
                "symbol": symbol,
            }

        side = "SELL" if net_qty > 0 else "BUY"
        qty = abs(net_qty)

        price = kwargs.get(
            "price",
            pos.get("avg_price", 0.0),
        )

        fee = kwargs.get("fee", 0.0)

        return self.place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            fee=fee,
            meta={"close": True},
        )

    # =========================================================
    # INTERNAL
    # =========================================================

    def _apply_fill(
        self,
        symbol,
        side,
        qty,
        price,
        fee
    ):

        current = self.positions.get(
            symbol,
            {
                "net_qty": 0,
                "avg_price": 0.0,
            },
        )

        current_qty = int(
            current["net_qty"]
        )

        current_avg = float(
            current["avg_price"]
        )

        signed_fill = qty if side == "BUY" else -qty
        new_qty = current_qty + signed_fill

        if side == "BUY":
            self.cash_balance = quantize(
                self.cash_balance
                - ((price * qty) + fee),
                4,
            )
        else:
            self.cash_balance = quantize(
                self.cash_balance
                + ((price * qty) - fee),
                4,
            )

        self.fees_paid = quantize(
            self.fees_paid + fee,
            4,
        )

        realized_pnl = 0.0

        if current_qty == 0:
            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": price,
            }
            return realized_pnl

        same_direction = (
            (current_qty > 0 and signed_fill > 0)
            or
            (current_qty < 0 and signed_fill < 0)
        )

        if same_direction:
            total_qty = (
                abs(current_qty)
                + abs(signed_fill)
            )

            weighted_cost = (
                (abs(current_qty) * current_avg)
                +
                (abs(signed_fill) * price)
            )

            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": quantize(
                    weighted_cost / total_qty,
                    4,
                ),
            }

            return realized_pnl

        closing_qty = min(
            abs(current_qty),
            abs(signed_fill),
        )

        direction = 1 if current_qty > 0 else -1

        realized_pnl = quantize(
            closing_qty
            * (price - current_avg)
            * direction,
            4,
        )

        self.realized_pnl = quantize(
            self.realized_pnl + realized_pnl,
            4,
        )

        if new_qty == 0:
            self.positions.pop(symbol, None)

        elif (
            (current_qty > 0 and new_qty > 0)
            or
            (current_qty < 0 and new_qty < 0)
        ):
            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": quantize(
                    current_avg,
                    4,
                ),
            }

        else:
            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": price,
            }

        return realized_pnl