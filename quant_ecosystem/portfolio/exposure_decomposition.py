class PortfolioExposureDecomposition:

    def gross_exposure(
        self,
        positions,
    ):
        return sum(
            abs(
                float(
                    p.get(
                        "market_value",
                        0.0,
                    )
                )
            )
            for p in positions
        )

    def net_exposure(
        self,
        positions,
    ):
        return sum(
            float(
                p.get(
                    "market_value",
                    0.0,
                )
            )
            for p in positions
        )

    def long_exposure(
        self,
        positions,
    ):
        return sum(
            float(
                p.get(
                    "market_value",
                    0.0,
                )
            )
            for p in positions
            if float(
                p.get(
                    "market_value",
                    0.0,
                )
            ) > 0
        )

    def short_exposure(
        self,
        positions,
    ):
        return abs(sum(
            float(
                p.get(
                    "market_value",
                    0.0,
                )
            )
            for p in positions
            if float(
                p.get(
                    "market_value",
                    0.0,
                )
            ) < 0
        ))

    def asset_class_breakdown(
        self,
        positions,
    ):
        buckets = {}

        for pos in positions:
            asset = pos.get(
                "asset_class",
                "UNKNOWN",
            )

            value = abs(float(
                pos.get(
                    "market_value",
                    0.0,
                )
            ))

            buckets[asset] = (
                buckets.get(asset, 0.0)
                + value
            )

        return buckets

    def symbol_concentration(
        self,
        positions,
    ):
        gross = self.gross_exposure(
            positions
        )

        if gross == 0:
            return {}

        result = {}

        for pos in positions:
            symbol = pos.get(
                "symbol",
                "UNKNOWN",
            )

            exposure = abs(float(
                pos.get(
                    "market_value",
                    0.0,
                )
            ))

            result[symbol] = (
                exposure / gross
            ) * 100.0

        return result

    def directional_delta(
        self,
        positions,
    ):
        total = 0.0

        for pos in positions:
            delta = float(
                pos.get("delta", 1.0)
            )

            qty = float(
                pos.get("qty", 0)
            )

            total += delta * qty

        return total

    def exposure_summary(
        self,
        positions,
    ):
        gross = self.gross_exposure(
            positions
        )

        net = self.net_exposure(
            positions
        )

        long_exp = self.long_exposure(
            positions
        )

        short_exp = self.short_exposure(
            positions
        )

        return {
            "gross_exposure": gross,
            "net_exposure": net,
            "long_exposure": long_exp,
            "short_exposure": short_exp,
            "asset_breakdown": (
                self.asset_class_breakdown(
                    positions
                )
            ),
            "symbol_concentration": (
                self.symbol_concentration(
                    positions
                )
            ),
            "directional_delta": (
                self.directional_delta(
                    positions
                )
            ),
        }


portfolio_exposure_decomposition = (
    PortfolioExposureDecomposition()
)