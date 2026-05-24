"""
QE3 OMS order registry
Pack22
"""

from typing import Dict

from quant_ecosystem.oms.order_models import CanonicalOrderLifecycle


class OrderRegistry:
    def __init__(self):
        self._orders: Dict[str, CanonicalOrderLifecycle] = {}
        self._fingerprints = set()

    def register(self, order: CanonicalOrderLifecycle):
        if order.order_id in self._orders:
            raise ValueError("duplicate order_id")

        self._orders[order.order_id] = order

    def get(self, order_id: str):
        return self._orders.get(order_id)

    def list_orders(self):
        return list(self._orders.values())

    def clear(self):
        self._orders.clear()
        self._fingerprints.clear()

    def fingerprint_exists(self, fingerprint: str):
        return fingerprint in self._fingerprints

    def add_fingerprint(self, fingerprint: str):
        self._fingerprints.add(fingerprint)


order_registry = OrderRegistry()