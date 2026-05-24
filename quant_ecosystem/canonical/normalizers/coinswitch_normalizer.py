"""
QE3 CoinSwitch Canonical Normalizer
Pack19 — Unified Data Canonicalization Layer
"""

from quant_ecosystem.canonical.broker_models import (
    CanonicalBalance,
    CanonicalExecution,
    CanonicalOrder,
    CanonicalPosition,
)

from quant_ecosystem.canonical.market_models import (
    CanonicalLTP,
    CanonicalOHLCVBar,
    CanonicalOHLCVSeries,
    CanonicalOrderBook,
    CanonicalOrderBookLevel,
    CanonicalQuote,
)

from quant_ecosystem.canonical.normalizers.base_normalizer import (
    BaseCanonicalNormalizer,
)


class CoinSwitchCanonicalNormalizer(BaseCanonicalNormalizer):

    @property
    def provider_name(self):
        return "coinswitch"

    def normalize_ltp(
        self,
        payload,
        symbol,
        market,
        asset_class="CRYPTO",
    ):
        price = (
            payload.get("last_price")
            or payload.get("ltp")
            or payload.get("price")
            or 0
        )

        return CanonicalLTP(
            provider=self.provider_name,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
            price=price,
            raw_payload=payload,
        )

    def normalize_quote(
        self,
        payload,
        symbol,
        market,
        asset_class="CRYPTO",
    ):
        return CanonicalQuote(
            provider=self.provider_name,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
            bid=payload.get("best_bid", 0),
            ask=payload.get("best_ask", 0),
            bid_size=payload.get("best_bid_qty", 0),
            ask_size=payload.get("best_ask_qty", 0),
            open=payload.get("open", 0),
            high=payload.get("high", 0),
            low=payload.get("low", 0),
            close=payload.get("close", 0),
            prev_close=payload.get("prev_close", 0),
            volume=payload.get("volume", 0),
            oi=0,
            raw_payload=payload,
        )

    def normalize_ohlcv(
        self,
        payload,
        symbol,
        market,
        asset_class="CRYPTO",
        interval="1m",
    ):
        candles = payload.get("candles", payload.get("data", []))

        bars = []

        for row in candles:
            if isinstance(row, dict):
                bars.append(
                    CanonicalOHLCVBar(
                        timestamp=row.get("timestamp"),
                        open=row.get("open"),
                        high=row.get("high"),
                        low=row.get("low"),
                        close=row.get("close"),
                        volume=row.get("volume", 0),
                    )
                )
            else:
                bars.append(
                    CanonicalOHLCVBar(
                        timestamp=row[0],
                        open=row[1],
                        high=row[2],
                        low=row[3],
                        close=row[4],
                        volume=row[5] if len(row) > 5 else 0,
                    )
                )

        return CanonicalOHLCVSeries(
            provider=self.provider_name,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
            interval=interval,
            bars=bars,
            raw_payload=payload,
        )

    def normalize_orderbook(
        self,
        payload,
        symbol,
        market,
        asset_class="CRYPTO",
    ):
        bids = []
        asks = []

        for x in payload.get("bids", []):
            if isinstance(x, dict):
                bids.append(
                    CanonicalOrderBookLevel(
                        price=x.get("price", 0),
                        qty=x.get("qty", 0),
                    )
                )
            else:
                bids.append(
                    CanonicalOrderBookLevel(
                        price=x[0],
                        qty=x[1],
                    )
                )

        for x in payload.get("asks", []):
            if isinstance(x, dict):
                asks.append(
                    CanonicalOrderBookLevel(
                        price=x.get("price", 0),
                        qty=x.get("qty", 0),
                    )
                )
            else:
                asks.append(
                    CanonicalOrderBookLevel(
                        price=x[0],
                        qty=x[1],
                    )
                )

        return CanonicalOrderBook(
            provider=self.provider_name,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
            bids=bids,
            asks=asks,
            depth=max(len(bids), len(asks)),
            raw_payload=payload,
        )

    def normalize_balance(self, payload):
        return CanonicalBalance(
            provider=self.provider_name,
            cash=payload.get("available_balance", 0),
            margin_available=payload.get("available_balance", 0),
            margin_used=0,
            collateral=0,
            currency=payload.get("currency", "INR"),
            raw_payload=payload,
        )

    def normalize_position(self, payload):
        qty = payload.get("quantity", 0)

        return CanonicalPosition(
            provider=self.provider_name,
            symbol=payload.get("symbol", ""),
            qty=qty,
            avg_price=payload.get("avg_buy_price", 0),
            ltp=payload.get("ltp", 0),
            unrealized_pnl=payload.get("unrealized_pnl", 0),
            realized_pnl=payload.get("realized_pnl", 0),
            side="BUY" if qty >= 0 else "SELL",
            product_type="SPOT",
            raw_payload=payload,
        )

    def normalize_order(self, payload):
        return CanonicalOrder(
            provider=self.provider_name,
            order_id=payload.get("order_id", ""),
            symbol=payload.get("symbol", ""),
            side=payload.get("side", "BUY"),
            qty=payload.get("quantity", 0),
            filled_qty=payload.get("filled_quantity", 0),
            remaining_qty=payload.get("remaining_quantity", 0),
            avg_price=payload.get("average_price", 0),
            status=payload.get("status", "PENDING"),
            order_type=payload.get("order_type", "MARKET"),
            product="SPOT",
            raw_payload=payload,
        )

    def normalize_execution(self, payload):
        return CanonicalExecution(
            provider=self.provider_name,
            execution_id=payload.get("trade_id", ""),
            order_id=payload.get("order_id", ""),
            symbol=payload.get("symbol", ""),
            qty=payload.get("quantity", 0),
            price=payload.get("price", 0),
            fees=payload.get("fee", 0),
            raw_payload=payload,
        )