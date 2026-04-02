from collections import defaultdict


class AlphaBook:

    def __init__(self):
        self.live_alphas = []
        self.allocations = defaultdict(float)
        self.pnl = defaultdict(float)

    def add(self, genome, allocation):
        self.live_alphas.append(genome)
        self.allocations[genome] = allocation

    def remove(self, genome):
        if genome in self.live_alphas:
            self.live_alphas.remove(genome)

    def update_pnl(self, genome, pnl):
        self.pnl[genome] += pnl

    def total_capital_used(self):
        return sum(self.allocations.values())