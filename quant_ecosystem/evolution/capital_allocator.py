class CapitalIntelligenceEngine:

    def __init__(self, portfolio_engine):
        self.portfolio_engine = portfolio_engine

    def optimize(self):

        allocations = self.portfolio_engine.get_allocations()

        total = sum(allocations.values()) if allocations else 0

        if total == 0:
            return allocations

        normalized = {k: v/total for k, v in allocations.items()}

        return normalized