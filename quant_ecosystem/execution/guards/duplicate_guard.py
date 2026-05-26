import time


class DuplicateOrderGuard:

    def __init__(self):
        self._recent_orders = {}

    def check(
        self,
        symbol,
        side,
        qty,
        window=10,
    ):
        key = f"{symbol}:{side}:{qty}"
        now = time.time()

        last = self._recent_orders.get(key)

        if last and (now - last) < window:
            raise RuntimeError(
                "Duplicate order blocked"
            )

        self._recent_orders[key] = now

    def clear(self):
        self._recent_orders.clear()