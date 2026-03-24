class Genome:

    def __init__(
        self,
        symbol,
        resolution,
        family,
        parameters,
        trained_regime=None,
    ):
        self.symbol = symbol
        self.resolution = resolution
        self.family = family
        self.parameters = parameters

        self.trained_regime = trained_regime

        self.fitness_score = 0.5
        self.alpha_confidence = 0.5

        self.sharpe = 1.0
        self.max_dd = 0.2
        self.volatility = 1.0

    # placeholder signal generator
    def generate_signal(self, snapshot):
        return None