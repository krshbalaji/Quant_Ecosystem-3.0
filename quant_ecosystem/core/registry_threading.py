from threading import RLock
from typing import Generic, TypeVar

from .base_registry import BaseRegistry


K = TypeVar("K")
V = TypeVar("V")


class ThreadSafeRegistry(
    BaseRegistry[K, V],
    Generic[K, V],
):

    def __init__(self) -> None:
        super().__init__()
        self._lock = RLock()

    def register(
        self,
        key: K,
        value: V,
    ) -> None:

        with self._lock:
            super().register(
                key,
                value,
            )

    def get(
        self,
        key: K,
    ) -> V:

        with self._lock:
            return super().get(key)

    def exists(
        self,
        key: K,
    ) -> bool:

        with self._lock:
            return super().exists(key)

    def snapshot(self) -> dict[K, V]:

        with self._lock:
            return dict(self._items)