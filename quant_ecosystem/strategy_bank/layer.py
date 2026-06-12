"""Strategy bank micro-layer adapter."""


class StrategyBankLayer:
    """Facade over existing strategy bank engine with safe fallbacks."""

    def __init__(self, bank_engine=None, **kwargs):
        self.bank_engine = bank_engine

    def is_enabled(self):
        return bool(self.bank_engine and getattr(self.bank_engine, "enabled", False))

    def active_strategies(self):
        bank = self.bank_engine
        if bank is None:
            return []
        return bank.get_active_strategies()

    def allocation(self, strategy_id):
        bank = self.bank_engine
        if bank is None:
            return 0.0
        return float(bank.get_allocation(strategy_id))

    def update_metrics(self, strategy_id, metrics):
        bank = self.bank_engine
        if bank is not None:
            bank.update_performance(strategy_id, metrics)

    def registry_rows(self):
        bank = self.bank_engine
        if bank is None:
            return []

        registry = getattr(bank, "registry", None)
        if registry is None:
            return []

        return registry.all()