"""
QE3 Market Data Router
Pack18
"""

from typing import Dict, Any, List, Optional

from quant_ecosystem.market.base_market_data import BaseMarketData


class MarketDataRouter:
    def __init__(self):
        self._providers: Dict[str, BaseMarketData] = {}
        self._health_cache: Dict[str, bool] = {}

    # ---------------------------------------------------------
    # Provider registration
    # ---------------------------------------------------------

    def register_provider(self, provider: BaseMarketData) -> None:
        if not isinstance(provider, BaseMarketData):
            raise RuntimeError("Provider must inherit BaseMarketData")

        name = provider.provider_name().lower()
        self._providers[name] = provider
        self._health_cache[name] = True

    def unregister_provider(self, provider_name: str) -> None:
        name = provider_name.lower()
        self._providers.pop(name, None)
        self._health_cache.pop(name, None)

    def list_providers(self) -> List[str]:
        return sorted(self._providers.keys())

    def provider_details(self) -> Dict[str, Any]:
        return {
            name: provider.get_capabilities().to_dict()
            for name, provider in self._providers.items()
        }

    # ---------------------------------------------------------
    # Provider selection
    # ---------------------------------------------------------

    def _eligible_providers(
        self,
        market: str,
        asset_class: str,
        feature: str,
    ) -> List[BaseMarketData]:
        eligible = []

        for provider in self._providers.values():
            if not provider.supports_market(market):
                continue

            if not provider.supports_asset(asset_class):
                continue

            if not provider.supports_feature(feature):
                continue

            if not self._health_cache.get(
                provider.provider_name().lower(),
                True
            ):
                continue

            eligible.append(provider)

        eligible.sort(
            key=lambda p: p.get_capabilities().priority_rank
        )

        return eligible

    # ---------------------------------------------------------
    # Failover executor
    # ---------------------------------------------------------

    def _execute_with_failover(
        self,
        method_name: str,
        route_market: str,
        route_asset_class: str,
        feature: str,
        **provider_kwargs,
    ):
        providers = self._eligible_providers(
            market=route_market,
            asset_class=route_asset_class,
            feature=feature,
        )

        if not providers:
            raise RuntimeError(
                f"No provider supports "
                f"market={route_market}, "
                f"asset={route_asset_class}, "
                f"feature={feature}"
            )

        last_exc = None

        for provider in providers:
            try:
                method = getattr(provider, method_name)
                result = method(**provider_kwargs)

                self._health_cache[
                    provider.provider_name().lower()
                ] = True

                return result

            except Exception as exc:
                self._health_cache[
                    provider.provider_name().lower()
                ] = False
                last_exc = exc

        raise RuntimeError(
            f"All providers failed for feature={feature}: {last_exc}"
        )

    # ---------------------------------------------------------
    # Public APIs
    # ---------------------------------------------------------

    def get_quote(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> Dict[str, Any]:
        return self._execute_with_failover(
            method_name="get_quote",
            route_market=market,
            route_asset_class=asset_class,
            feature="quote",
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

    def get_ltp(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ) -> float:
        return self._execute_with_failover(
            method_name="get_ltp",
            route_market=market,
            route_asset_class=asset_class,
            feature="ltp",
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        market: str,
        asset_class: str,
        bars: int = 100,
    ):
        return self._execute_with_failover(
            method_name="get_ohlcv",
            route_market=market,
            route_asset_class=asset_class,
            feature="ohlcv",
            symbol=symbol,
            timeframe=timeframe,
            market=market,
            asset_class=asset_class,
            bars=bars,
        )

    def get_orderbook(
        self,
        symbol: str,
        market: str,
        asset_class: str,
    ):
        return self._execute_with_failover(
            method_name="get_orderbook",
            route_market=market,
            route_asset_class=asset_class,
            feature="orderbook",
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

    def get_option_chain(
        self,
        symbol: str,
        market: str,
    ):
        return self._execute_with_failover(
            method_name="get_option_chain",
            route_market=market,
            route_asset_class="OPTIONS",
            feature="options_chain",
            symbol=symbol,
            market=market,
        )

    def get_fundamentals(
        self,
        symbol: str,
        market: str,
    ):
        return self._execute_with_failover(
            method_name="get_fundamentals",
            route_market=market,
            route_asset_class="EQUITY",
            feature="fundamentals",
            symbol=symbol,
            market=market,
        )

    # ---------------------------------------------------------
    # Health
    # ---------------------------------------------------------

    def health_check(self):
        output = {}

        for name, provider in self._providers.items():
            try:
                result = provider.health_check()
                healthy = bool(result.get("healthy", False))

                self._health_cache[name] = healthy
                output[name] = result

            except Exception as exc:
                self._health_cache[name] = False
                output[name] = {
                    "provider": name,
                    "healthy": False,
                    "message": str(exc),
                }

        return output

    def reset_provider_health(
        self,
        provider_name: Optional[str] = None,
    ):
        if provider_name:
            self._health_cache[provider_name.lower()] = True
            return

        for name in self._providers:
            self._health_cache[name] = True