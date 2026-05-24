import pytest

from quant_ecosystem.market.market_data_router import MarketDataRouter
from quant_ecosystem.market.base_market_data import BaseMarketData
from quant_ecosystem.market.market_capabilities import MarketCapabilities


class DummyMarketProvider(BaseMarketData):
    def __init__(
        self,
        provider_name,
        markets,
        assets,
        features,
        priority=10,
        should_fail=False,
    ):
        self._provider_name = provider_name
        self._should_fail = should_fail

        caps = MarketCapabilities(
            provider_name=provider_name,
            supported_markets=markets,
            supported_assets=assets,
            supports_quote="quote" in features,
            supports_ltp="ltp" in features,
            supports_ohlcv="ohlcv" in features,
            supports_orderbook="orderbook" in features,
            supports_streaming="streaming" in features,
            supports_options_chain="options_chain" in features,
            priority_rank=priority,
        )

        self._capabilities = caps
        self.capabilities = caps

    @property
    def name(self):
        return self._provider_name

    def define_capabilities(self):
        return self._capabilities


    def get_capabilities(self):
        return self._capabilities

    def health_check(self):
        return {
            "provider": self._provider_name,
            "healthy": not self._should_fail,
        }

    def get_quote(self, symbol, market, asset_class="EQUITY", **kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} quote failure")

        return {
            "provider": self._provider_name,
            "feature": "quote",
            "symbol": symbol,
            "market": market,
        }

    def get_ltp(self, symbol, market, asset_class="EQUITY", **kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} ltp failure")

        return 123.45

    def get_ohlcv(
        self,
        symbol,
        market,
        asset_class="EQUITY",
        interval="1m",
        **kwargs
    ):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} ohlcv failure")

        return [
            {
                "open": 100,
                "high": 110,
                "low": 95,
                "close": 105,
                "volume": 1000,
            }
        ]

    def get_orderbook(self, symbol, market, asset_class="EQUITY", **kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} orderbook failure")

        return {
            "bids": [],
            "asks": [],
        }

    def get_option_chain(self, symbol, market, **kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} option chain failure")

        return {
            "calls": [],
            "puts": [],
        }

    def get_fundamentals(self, symbol, market, **kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} fundamentals failure")

        return {
            "provider": self._provider_name,
            "pe": 21.3,
        }

    def get_news(self, symbol=None, market=None, **kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self._provider_name} news failure")

        return [
            {
                "headline": "dummy news"
            }
        ]


@pytest.fixture
def router():
    return MarketDataRouter()


def test_provider_registration(router):
    provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
    )

    router.register_provider(provider)

    assert "fyers" in router.list_providers()


def test_provider_capability_filtering(router):
    india_provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
    )

    us_provider = DummyMarketProvider(
        provider_name="viewtrade",
        markets=["US"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
    )

    router.register_provider(india_provider)
    router.register_provider(us_provider)

    result = router.get_quote(
        symbol="AAPL",
        market="US",
        asset_class="EQUITY",
    )

    assert result["provider"] == "viewtrade"


def test_india_routing(router):
    provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
    )

    router.register_provider(provider)

    result = router.get_quote(
        symbol="NSE:SBIN-EQ",
        market="INDIA",
        asset_class="EQUITY",
    )

    assert result["provider"] == "fyers"


def test_us_routing(router):
    provider = DummyMarketProvider(
        provider_name="viewtrade",
        markets=["US"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
    )

    router.register_provider(provider)

    result = router.get_quote(
        symbol="AAPL",
        market="US",
        asset_class="EQUITY",
    )

    assert result["provider"] == "viewtrade"


def test_crypto_routing(router):
    provider = DummyMarketProvider(
        provider_name="coinswitch",
        markets=["CRYPTO"],
        assets=["CRYPTO"],
        features=["quote"],
        priority=1,
    )

    router.register_provider(provider)

    result = router.get_quote(
        symbol="BTC-INR",
        market="CRYPTO",
        asset_class="CRYPTO",
    )

    assert result["provider"] == "coinswitch"


def test_provider_failover(router):
    failing_provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
        should_fail=True,
    )

    fallback_provider = DummyMarketProvider(
        provider_name="groww",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=2,
    )

    router.register_provider(failing_provider)
    router.register_provider(fallback_provider)

    result = router.get_quote(
        symbol="NSE:ITC-EQ",
        market="INDIA",
        asset_class="EQUITY",
    )

    assert result["provider"] == "groww"


def test_health_cache_blocks_failed_provider(router):
    failing_provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
        should_fail=True,
    )

    fallback_provider = DummyMarketProvider(
        provider_name="groww",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=2,
    )

    router.register_provider(failing_provider)
    router.register_provider(fallback_provider)

    router.get_quote(
        symbol="NSE:ITC-EQ",
        market="INDIA",
        asset_class="EQUITY",
    )

    result = router.get_quote(
        symbol="NSE:RELIANCE-EQ",
        market="INDIA",
        asset_class="EQUITY",
    )

    assert result["provider"] == "groww"


def test_reset_provider_health(router):
    failing_provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
        priority=1,
        should_fail=True,
    )

    router.register_provider(failing_provider)

    with pytest.raises(Exception):
        router.get_quote(
            symbol="NSE:ITC-EQ",
            market="INDIA",
            asset_class="EQUITY",
        )

    router.reset_provider_health("fyers")

    assert router._health_cache["fyers"] is True


def test_unsupported_market_rejection(router):
    provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
    )

    router.register_provider(provider)

    with pytest.raises(Exception, match="No provider supports"):
        router.get_quote(
            symbol="AAPL",
            market="US",
            asset_class="EQUITY",
        )


def test_unsupported_feature_rejection(router):
    provider = DummyMarketProvider(
        provider_name="fyers",
        markets=["INDIA"],
        assets=["EQUITY"],
        features=["quote"],
    )

    router.register_provider(provider)

    with pytest.raises(Exception, match="No provider supports"):
        router.get_fundamentals(
            symbol="NSE:SBIN-EQ",
            market="INDIA",
        )