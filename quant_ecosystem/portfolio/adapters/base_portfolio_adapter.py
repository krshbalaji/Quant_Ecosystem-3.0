"""
Base portfolio adapter contract
"""

from abc import ABC, abstractmethod


class BasePortfolioAdapter(ABC):

    @abstractmethod
    def translate_positions(self, raw):
        pass

    @abstractmethod
    def translate_balances(self, raw):
        pass

    @abstractmethod
    def translate_margin(self, raw):
        pass

    @abstractmethod
    def translate_portfolio_snapshot(self, raw):
        pass