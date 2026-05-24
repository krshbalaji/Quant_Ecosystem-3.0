"""
QE3 Groww Canonical Normalizer
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


class GrowwCanonicalNormalizer(BaseCanonicalNormalizer):

    @property
    def provider_name(self):
        return "groww"

    def normalize_ltp(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        price = (
            payload.get("ltp")
            or payload.get("last_price")
            or payload.get("price")
            or payload.get("close")
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
        asset_class="EQUITY",
    ):
        return CanonicalQuote(
            provider=self.provider_name,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
            bid=payload.get("bid", 0),
            ask=payload.get("ask", 0),
            bid_size=payload.get("bid_qty", 0),
            ask_size=payload.get("ask_qty", 0),
            open=payload.get("open", 0),
            high=payload.get("high", 0),
            low=payload.get("low", 0),
            close=payload.get("close", 0),
            prev_close=payload.get("prev_close", 0),
            volume=payload.get("volume", 0),
            oi=payload.get("oi", 0),
            raw_payload=payload,
        )

    def normalize_ohlcv(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
        interval="1m",
    ):
        candles = payload.get("candles", payload.get("data", []))

        bars = []

        for row in candles:
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
        asset_class="EQUITY",
    ):
        bids = []
        asks = []

        for x in payload.get("bids", []):
            bids.append(
                CanonicalOrderBookLevel(
                    price=x.get("price", 0),
                    qty=x.get("qty", 0),
                    orders=x.get("orders", 0),
                )
            )

        for x in payload.get("asks", []):
            asks.append(
                CanonicalOrderBookLevel(
                    price=x.get("price", 0),
                    qty=x.get("qty", 0),
                    orders=x.get("orders", 0),
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
            cash=payload.get("cash", 0),
            margin_available=payload.get("available_margin", 0),
            margin_used=payload.get("used_margin", 0),
            collateral=payload.get("collateral", 0),
            currency=payload.get("currency", "INR"),
            raw_payload=payload,
        )

    def normalize_position(self, payload):
        qty = payload.get("qty", 0)

        return CanonicalPosition(
            provider=self.provider_name,
            symbol=payload.get("symbol", ""),
            qty=qty,
            avg_price=payload.get("avg_price", 0),
            ltp=payload.get("ltp", 0),
            unrealized_pnl=payload.get("unrealized_pnl", 0),
            realized_pnl=payload.get("realized_pnl", 0),
            side="BUY" if qty >= 0 else "SELL",
            product_type=payload.get("product", "CNC"),
            raw_payload=payload,
        )

    def normalize_order(self, payload):
        return CanonicalOrder(
            provider=self.provider_name,
            order_id=payload.get("order_id", ""),
            symbol=payload.get("symbol", ""),
            side=payload.get("side", "BUY"),
            qty=payload.get("qty", 0),
            filled_qty=payload.get("filled_qty", 0),
            remaining_qty=payload.get("remaining_qty", 0),
            avg_price=payload.get("avg_price", 0),
            status=payload.get("status", "PENDING"),
            order_type=payload.get("order_type", "MARKET"),
            product=payload.get("product", "CNC"),
            raw_payload=payload,
        )

    def normalize_execution(self, payload):
        return CanonicalExecution(
            provider=self.provider_name,
            execution_id=payload.get("execution_id", ""),
            order_id=payload.get("order_id", ""),
            symbol=payload.get("symbol", ""),
            qty=payload.get("qty", 0),
            price=payload.get("price", 0),
            fees=payload.get("fees", 0),
            raw_payload=payload,
        )