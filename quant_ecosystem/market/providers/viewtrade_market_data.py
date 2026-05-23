"""
QE3 ViewTrade Market Data Provider
Pack18 — Market Data Unification Layer
US / Global Market Data
"""

from typing import Dict, Any, List

from quant_ecosystem.market.base_market_data import BaseMarketData
from quant_ecosystem.market.market_capabilities import MarketCapabilities


class ViewTradeMarketData(BaseMarketData):
    def __init__(self, viewtrade_client):
        self._client = viewtrade_client
        super().__init__()

    def define_capabilities(self) -> MarketCapabilities:
        return MarketCapabilities(
            provider_name="viewtrade",
            supported_markets=[
                "US",
                "GLOBAL",
            ],
            supported_assets=[
                "EQUITY",
                "ETF",
                "OPTIONS",
                "FOREX",
            ],
            supports_ltp=True,
            supports_quote=True,
            supports_ohlcv=True,
            supports_orderbook=True,
            supports_streaming=False,
            supports_options_chain=True,
            supports_fundamentals=True,
            supports_historical_data=True,
            supports_intraday_data=True,
            supports_health_check=True,
            supports_symbol_translation=True,
            requires_authentication=True,
            requires_session_refresh=True,
            max_symbols_per_request=100,
            max_history_bars=10000,
            priority_rank=10,
        )

    def normalize_symbol(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> str:
        if ":" in symbol:
            return symbol.split(":")[-1]
        return symbol.upper()

    def get_quote(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        symbol = self.normalize_symbol(symbol, market, asset_class)

        if not hasattr(self._client, "get_quote"):
            raise RuntimeError(
                "ViewTrade client missing get_quote()"
            )

        payload = self._client.get_quote(symbol)

        return {
            "provider": "viewtrade",
            "symbol": symbol,
            "ltp": float(payload.get("last", 0.0)),
            "bid": float(payload.get("bid", 0.0)),
            "ask": float(payload.get("ask", 0.0)),
            "volume": int(payload.get("volume", 0)),
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

        if not hasattr(self._client, "get_history"):
            raise RuntimeError(
                "ViewTrade client missing get_history()"
            )

        return self._client.get_history(
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
        quote = self.get_quote(symbol, market, asset_class)

        return {
            "provider": "viewtrade",
            "symbol": quote["symbol"],
            "bid": quote["bid"],
            "ask": quote["ask"],
            "depth": "L1",
        }

    def get_option_chain(
        self,
        symbol: str,
        market: str,
    ) -> Dict[str, Any]:
        symbol = self.normalize_symbol(symbol, market, "OPTIONS")

        if not hasattr(self._client, "get_option_chain"):
            raise RuntimeError(
                "ViewTrade client missing get_option_chain()"
            )

        return self._client.get_option_chain(symbol)

    def get_fundamentals(
        self,
        symbol: str,
        market: str,
    ) -> Dict[str, Any]:
        symbol = self.normalize_symbol(symbol, market, "EQUITY")

        if not hasattr(self._client, "get_fundamentals"):
            raise RuntimeError(
                "ViewTrade client missing get_fundamentals()"
            )

        return self._client.get_fundamentals(symbol)

    def health_check(self) -> Dict[str, Any]:
        try:
            self.get_quote("AAPL", "US", "EQUITY")

            return {
                "provider": "viewtrade",
                "healthy": True,
                "message": "ok",
            }

        except Exception as exc:
            return {
                "provider": "viewtrade",
                "healthy": False,
                "message": str(exc),
            }

    def authenticate(self) -> bool:
        if hasattr(self._client, "authenticate"):
            self._client.authenticate()
        return True

    def refresh_session(self) -> bool:
        if hasattr(self._client, "refresh_session"):
            self._client.refresh_session()
        return True