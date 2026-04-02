class PortfolioAllocator:

    def __init__(self, capital_governor):
        self.capital_governor = capital_governor

    def allocation_size(self, genome):

        base = self.capital_governor.allocate_alpha(genome)

        sharpe = getattr(genome, "sharpe", 1.0)

        vol_penalty = getattr(genome, "volatility", 1.0)

        adj = sharpe / (1 + vol_penalty)

        return base * adj