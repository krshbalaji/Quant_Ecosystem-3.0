"""Strategy bank micro-layer adapter."""


class StrategyBankLayer:
    """Facade over existing strategy bank engine with safe fallbacks."""

    def __init__(self, bank_engine=None):
        self.bank_engine = bank_engine

    def is_enabled(self):
        return bool(self.bank_engine and getattr(self.bank_engine, "enabled", False))

    def active_strategies(self):
        if not self.is_enabled():
            return []
        return self.bank_engine.get_active_strategies()

    def allocation(self, strategy_id):
        if not self.is_enabled():
            return 0.0
        return float(self.bank_engine.get_allocation(strategy_id))

    def update_metrics(self, strategy_id, metrics):
        if self.is_enabled():
            self.bank_engine.update_performance(strategy_id, metrics)

    def registry_rows(self):
        if not self.is_enabled():
            return []
        return self.bank_engine.registry.all()
