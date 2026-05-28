class PositionReconciler:
    """
    Institutional position truth reconciliation.
    """

    def reconcile(
        self,
        broker_name,
        broker,
        internal_positions,
    ):

        broker_positions = (
            self._fetch_positions(
                broker
            )
        )

        mismatches = []

        symbols = set(
            internal_positions.keys()
        ) | set(
            broker_positions.keys()
        )

        for symbol in symbols:

            internal_qty = (
                internal_positions.get(
                    symbol,
                    0,
                )
            )

            broker_qty = (
                broker_positions.get(
                    symbol,
                    0,
                )
            )

            if internal_qty != broker_qty:

                mismatches.append(
                    {
                        "broker": broker_name,
                        "symbol": symbol,
                        "internal_qty": internal_qty,
                        "broker_qty": broker_qty,
                    }
                )

        return {
            "matched": (
                len(mismatches) == 0
            ),
            "mismatches": mismatches,
        }

    def _fetch_positions(
        self,
        broker,
    ):

        if hasattr(
            broker,
            "get_positions",
        ):

            raw = broker.get_positions()

            if isinstance(raw, dict):
                return raw

            if isinstance(raw, list):

                normalized = {}

                for row in raw:

                    symbol = str(
                        row.get(
                            "symbol",
                            ""
                        )
                    )

                    qty = int(
                        row.get(
                            "qty",
                            0,
                        )
                    )

                    normalized[
                        symbol
                    ] = qty

                return normalized

        return {}