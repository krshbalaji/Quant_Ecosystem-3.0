from typing import Any, Dict, List


class MultiMapStore:
    """Minimal MultiMapStore backed by Dict[str, List[Any]].

    Methods: put, get, latest, keys, size
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[Any]] = {}

    def put(self, key: str, value: Any) -> None:
        lst = self._store.setdefault(key, [])
        lst.append(value)

    def get(self, key: str) -> List[Any]:
        return list(self._store.get(key, []))

    def latest(self, key: str):
        lst = self._store.get(key)
        if not lst:
            return None
        return lst[-1]

    def keys(self) -> List[str]:
        return list(self._store.keys())

    def size(self) -> int:
        return sum(len(v) for v in self._store.values())


__all__ = ["MultiMapStore"]
