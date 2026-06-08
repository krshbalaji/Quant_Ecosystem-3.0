"""
QE3 Canonical Base Normalizer
Pack19 — Unified Data Canonicalization Layer
"""

from abc import ABC, abstractmethod

from quant_ecosystem.canonical.market_models import (
    CanonicalLTP,
    CanonicalQuote,
    CanonicalOHLCVSeries,
    CanonicalOrderBook,
)

from quant_ecosystem.canonical.broker_models import (
    CanonicalBalance,
    CanonicalPosition,
    CanonicalOrder,
    CanonicalExecution,
)

class BaseCanonicalNormalizer(ABC):
    """
    Every provider-specific canonical normalizer
    must implement this contract.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def normalize_ltp(
        self,
        payload,
        symbol,
        market,
        asset_class: str = "EQUITY",
    ) -> CanonicalLTP:
        ...

    @abstractmethod
    def normalize_quote(
        self,
        payload,
        symbol,
        market,
        asset_class: str = "EQUITY",
    ) -> CanonicalQuote:
        ...

    @abstractmethod
    def normalize_ohlcv(
        self,
        payload,
        symbol,
        market,
        asset_class: str = "EQUITY",
        interval: str = "1m",
    ) -> CanonicalOHLCVSeries:
        ...

    @abstractmethod
    def normalize_orderbook(
        self,
        payload,
        symbol,
        market,
        asset_class: str = "EQUITY",
    ) -> CanonicalOrderBook:
        
        ...

    @abstractmethod
    def normalize_balance(self, payload) -> CanonicalBalance:
        ...

    @abstractmethod
    def normalize_position(self, payload) -> CanonicalPosition:
        ...

    @abstractmethod
    def normalize_order(self, payload) -> CanonicalOrder:
        ...

    @abstractmethod
    def normalize_execution(self, payload) -> CanonicalExecution:
        ...