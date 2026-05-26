import time


class DuplicateOrderGuard:

    def __init__(
        self,
        window=10,
    ):
        self._window = window
        self._recent = {}

    def check(
        self,
        symbol,
        side,
        qty,
    ):
        key = f"{symbol}:{side}:{qty}"
        now = time.time()

        last = self._recent.get(key)

        if last is not None:
            if (now - last) < self._window:
                raise RuntimeError(
                    "Duplicate order blocked"
                )

        self._recent[key] = now

    def clear(self):
        self._recent.clear()