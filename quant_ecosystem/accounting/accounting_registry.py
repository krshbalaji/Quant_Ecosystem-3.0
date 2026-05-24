"""
QE3 Accounting Registry
Pack23
"""

from typing import Dict

from quant_ecosystem.accounting.trade_models import (
    CanonicalAccountingSnapshot,
)


class AccountingRegistry:
    def __init__(self):
        self._snapshots: Dict[str, CanonicalAccountingSnapshot] = {}
        self._fills_seen = set()

    def get_snapshot(self, symbol: str):
        if symbol not in self._snapshots:
            self._snapshots[symbol] = CanonicalAccountingSnapshot()
        return self._snapshots[symbol]

    def mark_fill_seen(self, fill_id: str):
        self._fills_seen.add(fill_id)

    def fill_seen(self, fill_id: str):
        return fill_id in self._fills_seen

    def clear(self):
        self._snapshots.clear()
        self._fills_seen.clear()

    def all_snapshots(self):
        return self._snapshots


accounting_registry = AccountingRegistry()