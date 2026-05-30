from typing import Dict, Generic, TypeVar


K = TypeVar("K")
V = TypeVar("V")


class RegistryError(Exception):
    pass


class DuplicateRegistryKeyError(RegistryError):
    pass


class MissingRegistryKeyError(RegistryError):
    pass


class BaseRegistry(Generic[K, V]):

    def __init__(self) -> None:
        self._items: Dict[K, V] = {}

    def register(
        self,
        key: K,
        value: V,
    ) -> None:

        if key in self._items:
            raise DuplicateRegistryKeyError(
                f"Duplicate key: {key}"
            )

        self._items[key] = value

    def get(
        self,
        key: K,
    ) -> V:

        if key not in self._items:
            raise MissingRegistryKeyError(
                f"Missing key: {key}"
            )

        return self._items[key]

    def exists(
        self,
        key: K,
    ) -> bool:
        return key in self._items

    def count(self) -> int:
        return len(self._items)

    def items(self) -> dict[K, V]:
        return dict(self._items)