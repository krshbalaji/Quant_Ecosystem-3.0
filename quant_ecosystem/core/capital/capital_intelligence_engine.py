class CapitalIntelligenceEngine:
    """
    Dynamic capital allocator and risk optimizer.
    """

    def __init__(self, portfolio_engine, risk_engine):

        self.portfolio_engine = portfolio_engine
        self.risk_engine = risk_engine

    def evaluate(self):

        allocations = self.portfolio_engine.get_allocations()

        if not allocations:
            return

        total = sum(allocations.values())

        if total == 0:
            return allocations

        normalized = {
            k: v / total
            for k, v in allocations.items()
        }

        print("Capital Intelligence: optimized allocations")

        return normalized