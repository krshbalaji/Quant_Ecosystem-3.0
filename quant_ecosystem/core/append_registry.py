from typing import Generic, TypeVar

T = TypeVar("T")


class AppendRegistry(
    Generic[T]
):

    def __init__(self):
        self._items: list[T] = []

    def register(
        self,
        item: T,
    ) -> None:

        self._items.append(item)

    def entries(
        self,
    ) -> list[T]:

        return list(self._items)

    def count(
        self,
    ) -> int:

        return len(self._items)