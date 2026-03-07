"""Capital allocation micro-layer adapter."""


class CapitalAllocatorLayer:
    """Provides dynamic and optional manual allocation overlays."""

    def __init__(self, **kwargs):
        self._manual_allocations = {}

    def set_manual_allocation(self, strategy_id, pct):
        value = max(0.0, min(100.0, float(pct)))
        self._manual_allocations[str(strategy_id)] = round(value, 4)
        return self._manual_allocations[str(strategy_id)]

    def get_manual_allocation(self, strategy_id):
        return float(self._manual_allocations.get(str(strategy_id), 0.0))

    def snapshot(self):
        return dict(self._manual_allocations)
