# quant_ecosystem/core/keyed_registry.py

from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class KeyedRegistry(
    Generic[K, V]
):

    def __init__(self):
        self._items: dict[K, V] = {}

    def register(
        self,
        key: K,
        value: V,
    ) -> None:

        self._items[key] = value

    def get(
        self,
        key: K,
    ):

        return self._items.get(key)

    def exists(
        self,
        key: K,
    ) -> bool:

        return key in self._items

    def count(
        self,
    ) -> int:

        return len(self._items)

    def entries(
        self,
    ) -> dict[K, V]:

        return dict(self._items)