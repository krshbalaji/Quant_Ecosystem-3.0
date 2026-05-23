"""
QE3 FYERS Market Data Provider
Pack18 — Market Data Unification Layer
"""

from typing import Dict, Any, List

from quant_ecosystem.market.base_market_data import BaseMarketData
from quant_ecosystem.market.market_capabilities import MarketCapabilities


class FyersMarketData(BaseMarketData):
    def __init__(self, fyers_client):
        self._client = fyers_client
        super().__init__()

    def define_capabilities(self) -> MarketCapabilities:
        return MarketCapabilities(
            provider_name="fyers",
            supported_markets=["INDIA"],
            supported_assets=[
                "EQUITY",
                "OPTIONS",
                "FUTURES",
                "FOREX",
                "COMMODITY",
            ],
            supports_ltp=True,
            supports_quote=True,
            supports_ohlcv=True,
            supports_orderbook=True,
            supports_streaming=True,
            supports_options_chain=True,
            supports_historical_data=True,
            supports_intraday_data=True,
            supports_health_check=True,
            supports_symbol_translation=True,
            requires_authentication=True,
            requires_session_refresh=True,
            max_symbols_per_request=50,
            max_history_bars=10000,
            priority_rank=10,
        )

    def normalize_symbol(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> str:
        if symbol.startswith("NSE:") or symbol.startswith("BSE:"):
            return symbol
        return symbol

    def get_quote(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        symbol = self.normalize_symbol(symbol, market, asset_class)

        payload = self._client.quotes({"symbols": symbol})

        if payload.get("s") != "ok":
            raise RuntimeError(f"FYERS quote failed: {payload}")

        data = payload["d"][0]["v"]

        return {
            "provider": "fyers",
            "symbol": symbol,
            "ltp": float(data.get("lp", 0.0)),
            "bid": float(data.get("bid", 0.0)),
            "ask": float(data.get("ask", 0.0)),
            "volume": int(data.get("volume", 0)),
            "timestamp": data.get("tt"),
            "raw": payload,
        }

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        market: str,
        asset_class: str,
        bars: int = 100,
    ) -> List[Dict[str, Any]]:
        symbol = self.normalize_symbol(symbol, market, asset_class)

        interval_map = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "60m": "60",
            "1d": "D",
        }

        interval = interval_map.get(timeframe)

        if not interval:
            raise RuntimeError(
                f"Unsupported timeframe for FYERS: {timeframe}"
            )

        payload = self._client.history({
            "symbol": symbol,
            "resolution": interval,
            "date_format": "0",
            "range_from": "0",
            "range_to": "0",
            "cont_flag": "1",
        })

        if payload.get("s") != "ok":
            raise RuntimeError(f"FYERS history failed: {payload}")

        candles = payload.get("candles", [])[:bars]

        output = []

        for c in candles:
            output.append({
                "timestamp": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            })

        return output

    def get_orderbook(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        quote = self.get_quote(symbol, market, asset_class)

        return {
            "symbol": quote["symbol"],
            "bid": quote["bid"],
            "ask": quote["ask"],
            "provider": "fyers",
        }

    def get_option_chain(
        self,
        symbol: str,
        market: str,
    ) -> Dict[str, Any]:
        if hasattr(self._client, "optionchain"):
            payload = self._client.optionchain({
                "symbol": symbol
            })
            return payload

        raise RuntimeError("FYERS option chain API unavailable")

    def health_check(self) -> Dict[str, Any]:
        try:
            self.get_quote("NSE:SBIN-EQ", "INDIA", "EQUITY")
            return {
                "provider": "fyers",
                "healthy": True,
                "message": "ok",
            }
        except Exception as exc:
            return {
                "provider": "fyers",
                "healthy": False,
                "message": str(exc),
            }

    def authenticate(self) -> bool:
        return True

    def refresh_session(self) -> bool:
        if hasattr(self._client, "refresh_token"):
            self._client.refresh_token()
        return True