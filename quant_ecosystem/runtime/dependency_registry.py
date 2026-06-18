from typing import Optional

from quant_ecosystem.core.registry_threading import (
    ThreadSafeRegistry,
)


class DependencyRegistry(
    ThreadSafeRegistry[
        str,
        object,
    ]
):

    def register(
        self,
        key: str,
        value: object | None = None,
    ) -> None:

        if self.exists(key):
            return

        super().register(
            key,
            value,
        )

    def get(
        self,
        key: str,
    ) -> object | None:

        if not self.exists(key):
            return None

        return super().get(key)

    def all_services(self):

        return self.snapshot()

    def clear(self):

        with self._lock:
            self._items.clear()


dependency_registry = DependencyRegistry()