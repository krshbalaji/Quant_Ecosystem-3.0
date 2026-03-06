"""
PATCH: quant_ecosystem/strategy/strategy_bank_layer.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class StrategyBankLayer:
    """
    Maintains the registry of available strategies.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._strategies = {}

    def register(self, name: str, strategy):
        self._strategies[name] = strategy

    def get(self, name: str):
        return self._strategies.get(name)

    def all_strategies(self):
        return list(self._strategies.values())
