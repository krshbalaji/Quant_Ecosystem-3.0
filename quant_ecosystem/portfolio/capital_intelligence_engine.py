import logging
logger = logging.getLogger(name)

class CapitalIntelligenceEngine:
    """
    Manages capital allocation across strategies.
    """
    def __init__(self, initial_capital=1000000):

        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.strategy_allocations = {}

        logger.info("Capital Intelligence Engine initialized")

    def allocate(self, strategy_name, capital):

        if capital > self.available_capital:
            raise Exception("Not enough capital")

        self.strategy_allocations[strategy_name] = capital
        self.available_capital -= capital

    def release(self, strategy_name):

        capital = self.strategy_allocations.get(strategy_name, 0)

        self.available_capital += capital

        if strategy_name in self.strategy_allocations:
            del self.strategy_allocations[strategy_name]

    def summary(self):

        return {
            "initial_capital": self.initial_capital,
            "available_capital": self.available_capital,
            "allocations": self.strategy_allocations
        }