"""
QE3 Portfolio Adapter Registry
Pack21 — Portfolio/Risk Canonicalization
"""

from typing import Dict

from quant_ecosystem.portfolio.adapters.base_portfolio_adapter import BasePortfolioAdapter


class PortfolioAdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, BasePortfolioAdapter] = {}

    def register(self, broker: str, adapter: BasePortfolioAdapter):
        key = str(broker).strip().lower()
        if not key:
            raise ValueError("broker name required")
        self._adapters[key] = adapter

    def get(self, broker: str) -> BasePortfolioAdapter:
        key = str(broker).strip().lower()
        if key not in self._adapters:
            raise ValueError(f"unsupported broker: {broker}")
        return self._adapters[key]

    def list_adapters(self):
        return list(self._adapters.keys())

    def clear(self):
        self._adapters.clear()


portfolio_adapter_registry = PortfolioAdapterRegistry()