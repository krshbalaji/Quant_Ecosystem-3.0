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
        name,
        service,
    ):

        if self.exists(name):
            return

        super().register(
            name,
            service,
        )

    def get(
        self,
        name,
    ):

        if not self.exists(name):
            return None

        return super().get(name)

    def all_services(self):

        return self.snapshot()

    def clear(self):

        with self._lock:
            self._items.clear()


dependency_registry = (
    DependencyRegistry()
)