"""
QE3 Base Market Data Provider
Pack18 — Market Data Unification Layer

All market providers must inherit this class.

Future providers:
    - FYERS
    - Groww
    - Lemonn
    - ViewTrade
    - CoinSwitch
    - IBKR
    - Alpaca
    - Polygon
    - TwelveData
    - Binance
    - NSE direct
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from quant_ecosystem.market.market_capabilities import MarketCapabilities


class BaseMarketData(ABC):
    def __init__(self):
        self.capabilities = self.define_capabilities()

    @abstractmethod
    def define_capabilities(self) -> MarketCapabilities:
        """
        Provider declares capabilities here.
        """
        raise NotImplementedError

    def get_capabilities(self) -> MarketCapabilities:
        return self.capabilities

    def provider_name(self) -> str:
        return self.capabilities.provider_name

    def supports_market(self, market: str) -> bool:
        return self.capabilities.supports_market(market)

    def supports_asset(self, asset: str) -> bool:
        return self.capabilities.supports_asset(asset)

    def supports_feature(self, feature: str) -> bool:
        return self.capabilities.supports_feature(feature)

    @abstractmethod
    def get_quote(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        """
        Canonical quote response.

        Expected:
        {
            "symbol": "...",
            "ltp": float,
            "bid": float,
            "ask": float,
            "volume": int,
            "timestamp": "..."
        }
        """
        raise NotImplementedError

    def get_ltp(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> float:
        quote = self.get_quote(symbol, market, asset_class)
        return float(quote.get("ltp", 0.0))

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        market: str,
        asset_class: str,
        bars: int = 100,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            f"{self.provider_name()} does not support OHLCV"
        )

    def get_orderbook(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.provider_name()} does not support orderbook"
        )

    def get_option_chain(
        self,
        symbol: str,
        market: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.provider_name()} does not support option chain"
        )

    def get_fundamentals(
        self,
        symbol: str,
        market: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.provider_name()} does not support fundamentals"
        )

    def get_news(
        self,
        symbol: Optional[str] = None,
        market: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            f"{self.provider_name()} does not support news"
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Standard provider health contract.
        """
        return {
            "provider": self.provider_name(),
            "healthy": True,
            "message": "health check not implemented",
        }

    def authenticate(self) -> bool:
        """
        Optional auth/session init.
        """
        return True

    def refresh_session(self) -> bool:
        """
        Optional session refresh.
        """
        return True

    def normalize_symbol(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> str:
        """
        Override if provider requires symbol translation.
        """
        return symbol

    def batch_quotes(
        self,
        symbols: List[str],
        market: str,
        asset_class: str,
    ) -> List[Dict[str, Any]]:
        results = []

        max_allowed = self.capabilities.max_symbols_per_request

        if len(symbols) > max_allowed:
            raise RuntimeError(
                f"{self.provider_name()} max batch size exceeded"
            )

        for symbol in symbols:
            results.append(
                self.get_quote(
                    symbol=symbol,
                    market=market,
                    asset_class=asset_class,
                )
            )

        return results