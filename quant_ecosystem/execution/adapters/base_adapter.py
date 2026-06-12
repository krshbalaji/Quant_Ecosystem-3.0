"""
Base execution adapter contract
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseExecutionAdapter(ABC):

    @abstractmethod
    def translate_order(self, request) -> dict[str, Any]:
        ...

    @abstractmethod
    def translate_modify(self, request) -> dict[str, Any]:
        ...

    @abstractmethod
    def translate_cancel(self, request) -> dict[str, Any]:
        ...