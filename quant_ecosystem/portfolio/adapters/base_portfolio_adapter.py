"""
Base portfolio adapter contract
"""

from abc import ABC, abstractmethod
from canonical.broker_models import CanonicalBalance

class BasePortfolioAdapter(ABC):

    from typing import Any

    def translate_positions(self, raw: Any) -> list:
        raise NotImplementedError

    def translate_balances(self, raw: Any) -> CanonicalBalance:
        raise NotImplementedError

    def translate_margin(self, raw: Any) -> dict:
        raise NotImplementedError

    def translate_portfolio_snapshot(self, raw: Any) -> dict:
        raise NotImplementedError