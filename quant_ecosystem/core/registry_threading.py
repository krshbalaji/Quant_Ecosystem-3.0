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
        key,
        value=None,
    ):

        if value is None:

            value = key

            inferred_key = (
                getattr(value, "adapter_id", None)
                or getattr(value, "organism_id", None)
                or getattr(value, "entity_id", None)
                or getattr(value, "capability_id", None)
                or getattr(value, "workflow_id", None)
                or getattr(value, "dependency_id", None)
                or getattr(value, "integration_id", None)
                or getattr(value, "lineage_id", None)
                or getattr(value, "strategy_id", None)
                or getattr(value, "router_id", None)
                or getattr(value, "id", None)
                or getattr(value, "name", None)
                or getattr(value, "component_id", None)
                or getattr(value, "target_system", None)
            )

            if inferred_key is None:
                raise ValueError(
                    f"Unable to infer registry key from {type(value).__name__}"
                )

            key = inferred_key

        with self._lock:
            self._items[key] = value

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