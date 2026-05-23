"""
QE3 CoinSwitch Market Data Provider
Pack18 — Market Data Unification Layer
Crypto Market Data
"""

from typing import Dict, Any, List

from quant_ecosystem.market.base_market_data import BaseMarketData
from quant_ecosystem.market.market_capabilities import MarketCapabilities


class CoinSwitchMarketData(BaseMarketData):
    def __init__(self, coinswitch_client):
        self._client = coinswitch_client
        super().__init__()

    def define_capabilities(self) -> MarketCapabilities:
        return MarketCapabilities(
            provider_name="coinswitch",
            supported_markets=["CRYPTO"],
            supported_assets=["CRYPTO"],
            supports_ltp=True,
            supports_quote=True,
            supports_ohlcv=True,
            supports_orderbook=True,
            supports_streaming=True,
            supports_historical_data=True,
            supports_intraday_data=True,
            supports_level2_depth=True,
            supports_health_check=True,
            supports_symbol_translation=True,
            requires_authentication=True,
            requires_session_refresh=False,
            max_symbols_per_request=50,
            max_history_bars=20000,
            priority_rank=10,
        )

    def normalize_symbol(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> str:
        symbol = symbol.upper()

        if "/" in symbol:
            return symbol.replace("/", "-")

        return symbol

    def get_quote(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        symbol = self.normalize_symbol(symbol, market, asset_class)

        if not hasattr(self._client, "get_quote"):
            raise RuntimeError(
                "CoinSwitch client missing get_quote()"
            )

        payload = self._client.get_quote(symbol)

        return {
            "provider": "coinswitch",
            "symbol": symbol,
            "ltp": float(payload.get("last_price", 0.0)),
            "bid": float(payload.get("best_bid", 0.0)),
            "ask": float(payload.get("best_ask", 0.0)),
            "volume": float(payload.get("volume", 0.0)),
            "timestamp": payload.get("timestamp"),
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

        if not hasattr(self._client, "get_candles"):
            raise RuntimeError(
                "CoinSwitch client missing get_candles()"
            )

        return self._client.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            bars=bars,
        )

    def get_orderbook(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        symbol = self.normalize_symbol(symbol, market, asset_class)

        if not hasattr(self._client, "get_orderbook"):
            raise RuntimeError(
                "CoinSwitch client missing get_orderbook()"
            )

        payload = self._client.get_orderbook(symbol)

        return {
            "provider": "coinswitch",
            "symbol": symbol,
            "bids": payload.get("bids", []),
            "asks": payload.get("asks", []),
            "depth": "L2",
            "raw": payload,
        }

    def health_check(self) -> Dict[str, Any]:
        try:
            self.get_quote("BTC-INR", "CRYPTO", "CRYPTO")

            return {
                "provider": "coinswitch",
                "healthy": True,
                "message": "ok",
            }

        except Exception as exc:
            return {
                "provider": "coinswitch",
                "healthy": False,
                "message": str(exc),
            }

    def authenticate(self) -> bool:
        if hasattr(self._client, "authenticate"):
            self._client.authenticate()
        return True