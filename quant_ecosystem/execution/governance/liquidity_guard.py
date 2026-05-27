class LiquidityGuard:

    def __init__(
        self,
        max_spread_pct=2.0,
        min_depth=100,
    ):
        self._max_spread_pct = max_spread_pct
        self._min_depth = min_depth

    def ensure_liquid(
        self,
        broker,
        symbol,
        qty,
    ):
        if not hasattr(
            broker,
            "get_ltp",
        ):
            return

        try:
            quote = broker.get_ltp(
                symbol
            )

            ltp = float(
                quote.get(
                    "ltp",
                    0
                )
            )

            bid = float(
                quote.get(
                    "bid",
                    ltp
                )
            )

            ask = float(
                quote.get(
                    "ask",
                    ltp
                )
            )

            depth = int(
                quote.get(
                    "depth",
                    qty * 10
                )
            )

            spread = 0.0

            if ltp > 0:
                spread = (
                    (ask - bid) / ltp
                ) * 100

            if spread > self._max_spread_pct:
                raise RuntimeError(
                    f"ILLIQUID SPREAD: {spread:.2f}%"
                )

            if depth < max(
                qty,
                self._min_depth,
            ):
                raise RuntimeError(
                    f"INSUFFICIENT DEPTH: {depth}"
                )

        except RuntimeError:
            raise

        except Exception:
            return