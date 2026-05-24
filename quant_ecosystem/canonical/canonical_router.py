"""
QE3 Canonical Router
Pack19 — Unified Data Canonicalization Layer
"""

from quant_ecosystem.canonical.exceptions import (
    UnsupportedProviderError,
)

from quant_ecosystem.canonical.normalizers.coinswitch_normalizer import (
    CoinSwitchCanonicalNormalizer,
)

from quant_ecosystem.canonical.normalizers.fyers_normalizer import (
    FYERSCanonicalNormalizer,
)

from quant_ecosystem.canonical.normalizers.groww_normalizer import (
    GrowwCanonicalNormalizer,
)

from quant_ecosystem.canonical.normalizers.viewtrade_normalizer import (
    ViewTradeCanonicalNormalizer,
)


class CanonicalRouter:
    """
    Provider payload -> QE3 canonical truth router
    """

    def __init__(self):
        self._normalizers = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(FYERSCanonicalNormalizer())
        self.register(GrowwCanonicalNormalizer())
        self.register(ViewTradeCanonicalNormalizer())
        self.register(CoinSwitchCanonicalNormalizer())

    def register(self, normalizer):
        self._normalizers[
            normalizer.provider_name.lower()
        ] = normalizer

    def unregister(self, provider):
        key = provider.lower()

        if key in self._normalizers:
            del self._normalizers[key]

    def list_registered(self):
        return list(self._normalizers.keys())

    def has_provider(self, provider):
        return provider.lower() in self._normalizers

    def get(self, provider):
        key = provider.lower()

        if key not in self._normalizers:
            raise UnsupportedProviderError(
                f"Unsupported canonical provider: {provider}"
            )

        return self._normalizers[key]

    def normalize_ltp(
        self,
        provider,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        return self.get(provider).normalize_ltp(
            payload=payload,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

    def normalize_quote(
        self,
        provider,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        return self.get(provider).normalize_quote(
            payload=payload,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

    def normalize_ohlcv(
        self,
        provider,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
        interval="1m",
    ):
        return self.get(provider).normalize_ohlcv(
            payload=payload,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
            interval=interval,
        )

    def normalize_orderbook(
        self,
        provider,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        return self.get(provider).normalize_orderbook(
            payload=payload,
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

    def normalize_balance(
        self,
        provider,
        payload,
    ):
        return self.get(provider).normalize_balance(
            payload
        )

    def normalize_position(
        self,
        provider,
        payload,
    ):
        return self.get(provider).normalize_position(
            payload
        )

    def normalize_order(
        self,
        provider,
        payload,
    ):
        return self.get(provider).normalize_order(
            payload
        )

    def normalize_execution(
        self,
        provider,
        payload,
    ):
        return self.get(provider).normalize_execution(
            payload
        )