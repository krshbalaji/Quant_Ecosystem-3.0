class AdaptiveExecutionStrategy:

    def choose(
        self,
        broker,
        symbol,
        qty,
        price,
    ):
        if not hasattr(
            broker,
            "get_ltp",
        ):
            return "STANDARD"

        try:
            quote = broker.get_ltp(
                symbol
            )

            ltp = float(
                quote.get(
                    "ltp",
                    price
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

            spread = 0.0

            if ltp > 0:
                spread = (
                    (ask - bid) / ltp
                ) * 100

            if qty >= 5000:
                return "SPLIT"

            if spread > 1.0:
                return "PASSIVE_LIMIT"

            return "STANDARD"

        except Exception:
            return "STANDARD"