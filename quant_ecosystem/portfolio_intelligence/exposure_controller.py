from collections import defaultdict


class ExposureController:

    def __init__(self):
        self.family_exposure = defaultdict(float)
        self.symbol_exposure = defaultdict(float)

    def allow(self, genome, allocation):

        fam = genome.family
        sym = genome.symbol

        if self.family_exposure[fam] > 0.25:
            return False

        if self.symbol_exposure[sym] > 0.35:
            return False

        self.family_exposure[fam] += allocation
        self.symbol_exposure[sym] += allocation

        return True