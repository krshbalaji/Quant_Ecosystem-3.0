from quant_ecosystem.utils.decimal_utils import quantize


class PortfolioEngine:

    def __init__(self, **kwargs):
        self.positions = {}

    def _asset_bucket(self, asset_class):
        return str(asset_class or "EQUITY").upper()

    def apply_fill(
        self,
        symbol,
        side,
        qty,
        price,
        multiplier=1.0,
        asset_class="EQUITY",
    ):
        """
        Pack25 instrument-aware portfolio accounting.

        qty:
            execution quantity

        multiplier:
            contract multiplier / lot multiplier

        asset_class:
            EQUITY / OPTIONS / FUTURES / CRYPTO / FOREX
        """

        multiplier = float(multiplier or 1.0)
        asset_class = self._asset_bucket(asset_class)

        current = self.positions.get(
            symbol,
            {
                "net_qty": 0,
                "avg_price": 0.0,
                "multiplier": multiplier,
                "asset_class": asset_class,
            },
        )

        current_qty = int(current["net_qty"])
        current_avg = float(current["avg_price"])
        signed_fill = int(qty) if side == "BUY" else -int(qty)

        new_qty = current_qty + signed_fill

        if current_qty == 0:
            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": quantize(price, 4),
                "multiplier": multiplier,
                "asset_class": asset_class,
            }
            return {"realized_pnl": 0.0}

        same_direction = (
            (current_qty > 0 and signed_fill > 0)
            or
            (current_qty < 0 and signed_fill < 0)
        )

        if same_direction:
            total_qty = abs(current_qty) + abs(signed_fill)

            weighted_cost = (
                (abs(current_qty) * current_avg)
                +
                (abs(signed_fill) * price)
            )

            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": quantize(weighted_cost / total_qty, 4),
                "multiplier": multiplier,
                "asset_class": asset_class,
            }

            return {"realized_pnl": 0.0}

        closing_qty = min(abs(current_qty), abs(signed_fill))
        direction = 1 if current_qty > 0 else -1

        realized_pnl = (
            closing_qty
            * (price - current_avg)
            * direction
            * multiplier
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
                "avg_price": quantize(current_avg, 4),
                "multiplier": multiplier,
                "asset_class": asset_class,
            }

        else:
            self.positions[symbol] = {
                "net_qty": new_qty,
                "avg_price": quantize(price, 4),
                "multiplier": multiplier,
                "asset_class": asset_class,
            }

        return {
            "realized_pnl": quantize(realized_pnl, 4)
        }

    def market_value(self, latest_prices):
        value = 0.0

        for symbol, pos in self.positions.items():
            price = latest_prices.get(symbol)

            if price is None:
                continue

            multiplier = float(pos.get("multiplier", 1.0))

            value += (
                pos["net_qty"]
                * price
                * multiplier
            )

        return quantize(value, 4)

    def unrealized_pnl(self, latest_prices):
        pnl = 0.0

        for symbol, pos in self.positions.items():
            price = latest_prices.get(symbol)

            if price is None:
                continue

            multiplier = float(pos.get("multiplier", 1.0))

            pnl += (
                (price - pos["avg_price"])
                * pos["net_qty"]
                * multiplier
            )

        return quantize(pnl, 4)

    def net_exposure_notional(self, latest_prices):
        notional = 0.0

        for symbol, pos in self.positions.items():
            price = latest_prices.get(symbol)

            if price is None:
                continue

            multiplier = float(pos.get("multiplier", 1.0))

            notional += abs(
                pos["net_qty"]
                * price
                * multiplier
            )

        return quantize(notional, 4)

    def symbol_exposure_notional(self, symbol, latest_prices):
        position = self.positions.get(symbol)

        if not position:
            return 0.0

        price = latest_prices.get(symbol)

        if price is None:
            return 0.0

        multiplier = float(position.get("multiplier", 1.0))

        return quantize(
            abs(
                position["net_qty"]
                * price
                * multiplier
            ),
            4,
        )

    def asset_exposure_notional(
        self,
        asset_class,
        latest_prices,
    ):
        total = 0.0
        target_asset = self._asset_bucket(asset_class)

        for symbol, pos in self.positions.items():
            if self._asset_bucket(pos.get("asset_class")) != target_asset:
                continue

            price = latest_prices.get(symbol)

            if price is None:
                continue

            multiplier = float(pos.get("multiplier", 1.0))

            total += abs(
                pos["net_qty"]
                * price
                * multiplier
            )

        return quantize(total, 4)

    def get_allocations(self):
        if not self.positions:
            return {}

        return {
            symbol: abs(data.get("net_qty", 0))
            for symbol, data in self.positions.items()
        }

    def update_position(self, symbol, side, qty, price):
        return self.apply_fill(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
        )

    def snapshot(self):
        return {
            symbol: data.copy()
            for symbol, data in self.positions.items()
        }

    def exposure(self):
        return len(self.positions)

    def replace_positions(self, positions):
        updated = {}

        for item in positions:
            symbol = item["symbol"]

            updated[symbol] = {
                "net_qty": int(item["net_qty"]),
                "avg_price": quantize(float(item["avg_price"]), 4),
                "multiplier": float(item.get("multiplier", 1.0)),
                "asset_class": self._asset_bucket(
                    item.get("asset_class", "EQUITY")
                ),
            }

        self.positions = updated