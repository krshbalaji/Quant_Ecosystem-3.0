"""
Base execution adapter contract
"""

from abc import ABC, abstractmethod


class BaseExecutionAdapter(ABC):

    @abstractmethod
    def translate_order(self, request):
        pass

    @abstractmethod
    def translate_modify(self, request):
        pass

    @abstractmethod
    def translate_cancel(self, request):
        pass