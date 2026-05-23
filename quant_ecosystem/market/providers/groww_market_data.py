"""
QE3 Groww Market Data Provider
Pack18 — Market Data Unification Layer
"""

from typing import Dict, Any, List

from quant_ecosystem.market.base_market_data import BaseMarketData
from quant_ecosystem.market.market_capabilities import MarketCapabilities


class GrowwMarketData(BaseMarketData):
    def __init__(self, groww_client):
        self._client = groww_client
        super().__init__()

    def define_capabilities(self) -> MarketCapabilities:
        return MarketCapabilities(
            provider_name="groww",
            supported_markets=["INDIA"],
            supported_assets=[
                "EQUITY",
                "OPTIONS",
                "FUTURES",
                "ETF",
            ],
            supports_ltp=True,
            supports_quote=True,
            supports_ohlcv=True,
            supports_orderbook=False,
            supports_streaming=False,
            supports_options_chain=False,
            supports_historical_data=True,
            supports_intraday_data=True,
            supports_health_check=True,
            supports_symbol_translation=True,
            requires_authentication=True,
            max_symbols_per_request=20,
            max_history_bars=5000,
            priority_rank=20,
        )

    def normalize_symbol(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> str:
        return symbol

    def get_quote(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        if not hasattr(self._client, "get_quote"):
            raise RuntimeError(
                "Groww client missing get_quote implementation"
            )

        payload = self._client.get_quote(symbol)

        return {
            "provider": "groww",
            "symbol": symbol,
            "ltp": float(payload.get("ltp", 0.0)),
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
        if not hasattr(self._client, "get_history"):
            raise RuntimeError(
                "Groww client missing get_history implementation"
            )

        return self._client.get_history(
            symbol=symbol,
            timeframe=timeframe,
            bars=bars,
        )

    def health_check(self) -> Dict[str, Any]:
        try:
            self.get_quote("NSE:SBIN-EQ", "INDIA", "EQUITY")
            return {
                "provider": "groww",
                "healthy": True,
                "message": "ok",
            }
        except Exception as exc:
            return {
                "provider": "groww",
                "healthy": False,
                "message": str(exc),
            }