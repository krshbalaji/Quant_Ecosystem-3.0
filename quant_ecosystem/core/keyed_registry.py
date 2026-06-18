from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class KeyedRegistry(
    Generic[K, V]
):

    def __init__(self):
        self._items: dict[K, V] = {}

    from typing import Any

    def register(
        self,
        key: K | V,
        value: V | None = None,
    ) -> None:

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