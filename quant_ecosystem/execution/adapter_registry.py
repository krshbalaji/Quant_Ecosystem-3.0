"""
QE3 Execution Adapter Registry
Pack20 — Canonical Execution Refactor
"""

from typing import Dict

from quant_ecosystem.execution.adapters.base_adapter import BaseExecutionAdapter


class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, BaseExecutionAdapter] = {}

    def register(self, broker: str, adapter: BaseExecutionAdapter):
        key = str(broker).strip().lower()
        if not key:
            raise ValueError("broker name required")
        self._adapters[key] = adapter

    def get(self, broker: str) -> BaseExecutionAdapter:
        key = str(broker).strip().lower()
        if key not in self._adapters:
            raise ValueError(f"unsupported broker: {broker}")
        return self._adapters[key]

    def list_adapters(self):
        return list(self._adapters.keys())


adapter_registry = AdapterRegistry()