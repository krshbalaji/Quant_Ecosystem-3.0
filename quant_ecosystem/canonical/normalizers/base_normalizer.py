"""
QE3 Canonical Base Normalizer
Pack19 — Unified Data Canonicalization Layer
"""

from abc import ABC, abstractmethod


class BaseCanonicalNormalizer(ABC):
    """
    Every provider-specific canonical normalizer
    must implement this contract.
    """

    @property
    @abstractmethod
    def provider_name(self):
        pass

    @abstractmethod
    def normalize_ltp(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        pass

    @abstractmethod
    def normalize_quote(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        pass

    @abstractmethod
    def normalize_ohlcv(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
        interval="1m",
    ):
        pass

    @abstractmethod
    def normalize_orderbook(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        pass

    @abstractmethod
    def normalize_balance(self, payload):
        pass

    @abstractmethod
    def normalize_position(self, payload):
        pass

    @abstractmethod
    def normalize_order(self, payload):
        pass

    @abstractmethod
    def normalize_execution(self, payload):
        pass