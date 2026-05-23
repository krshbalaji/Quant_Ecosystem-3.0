"""
QE3 Market Provider Capability Contract
Pack18 — Market Data Unification Layer

Purpose:
    Standard contract every market data provider must expose.

Design goals:
    - Plug-and-play provider onboarding
    - Capability-driven routing
    - Future admin UI compatibility
    - Config-driven registration
    - Zero hardcoded provider assumptions
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class MarketCapabilities:
    provider_name: str

    supported_markets: List[str] = field(default_factory=list)
    supported_assets: List[str] = field(default_factory=list)

    supports_ltp: bool = False
    supports_quote: bool = True
    supports_ohlcv: bool = False
    supports_orderbook: bool = False
    supports_streaming: bool = False
    supports_options_chain: bool = False
    supports_fundamentals: bool = False
    supports_news: bool = False
    supports_corporate_actions: bool = False
    supports_market_breadth: bool = False
    supports_historical_data: bool = False
    supports_intraday_data: bool = False
    supports_level2_depth: bool = False

    supports_health_check: bool = True
    supports_rate_limit_awareness: bool = False
    supports_symbol_translation: bool = False

    requires_authentication: bool = True
    requires_session_refresh: bool = False

    max_symbols_per_request: int = 1
    max_history_bars: int = 1000

    priority_rank: int = 100

    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports_market(self, market: str) -> bool:
        return market.upper() in {
            x.upper() for x in self.supported_markets
        }

    def supports_asset(self, asset: str) -> bool:
        return asset.upper() in {
            x.upper() for x in self.supported_assets
        }

    def supports_feature(self, feature: str) -> bool:
        feature_map = {
            "ltp": self.supports_ltp,
            "quote": self.supports_quote,
            "ohlcv": self.supports_ohlcv,
            "orderbook": self.supports_orderbook,
            "streaming": self.supports_streaming,
            "options_chain": self.supports_options_chain,
            "fundamentals": self.supports_fundamentals,
            "news": self.supports_news,
            "corporate_actions": self.supports_corporate_actions,
            "market_breadth": self.supports_market_breadth,
            "historical_data": self.supports_historical_data,
            "intraday_data": self.supports_intraday_data,
            "level2_depth": self.supports_level2_depth,
        }

        return feature_map.get(feature.lower(), False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "supported_markets": self.supported_markets,
            "supported_assets": self.supported_assets,
            "supports_ltp": self.supports_ltp,
            "supports_quote": self.supports_quote,
            "supports_ohlcv": self.supports_ohlcv,
            "supports_orderbook": self.supports_orderbook,
            "supports_streaming": self.supports_streaming,
            "supports_options_chain": self.supports_options_chain,
            "supports_fundamentals": self.supports_fundamentals,
            "supports_news": self.supports_news,
            "supports_corporate_actions": self.supports_corporate_actions,
            "supports_market_breadth": self.supports_market_breadth,
            "supports_historical_data": self.supports_historical_data,
            "supports_intraday_data": self.supports_intraday_data,
            "supports_level2_depth": self.supports_level2_depth,
            "supports_health_check": self.supports_health_check,
            "supports_rate_limit_awareness": self.supports_rate_limit_awareness,
            "supports_symbol_translation": self.supports_symbol_translation,
            "requires_authentication": self.requires_authentication,
            "requires_session_refresh": self.requires_session_refresh,
            "max_symbols_per_request": self.max_symbols_per_request,
            "max_history_bars": self.max_history_bars,
            "priority_rank": self.priority_rank,
            "metadata": self.metadata,
        }