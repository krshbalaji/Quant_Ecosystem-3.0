class ExposureGovernor:

    def symbol_overlap(
        self,
        signals,
    ):
        exposure = {}

        for signal in signals:
            symbol = signal.get("symbol")
            side = str(
                signal.get("side", "")
            ).upper()

            if not symbol:
                continue

            exposure.setdefault(symbol, [])
            exposure[symbol].append(side)

        return exposure

    def directional_conflicts(
        self,
        signals,
    ):
        overlaps = self.symbol_overlap(signals)

        conflicts = {}

        for symbol, sides in overlaps.items():
            if "BUY" in sides and "SELL" in sides:
                conflicts[symbol] = sides

        return conflicts

    def concentration_check(
        self,
        allocations,
        max_pct=0.40,
        total_capital=1.0,
    ):
        breaches = {}

        total_capital = float(total_capital)

        if total_capital <= 0:
            return breaches

        for strategy_id, amount in allocations.items():
            pct = float(amount) / total_capital

            if pct > max_pct:
                breaches[strategy_id] = pct

        return breaches

    def gross_exposure(
        self,
        positions,
    ):
        total = 0.0

        for pos in positions:
            qty = abs(
                float(pos.get("qty", 0))
            )

            price = float(
                pos.get("price", 0)
            )

            multiplier = float(
                pos.get(
                    "multiplier",
                    1.0,
                )
            )

            total += (
                qty
                * price
                * multiplier
            )

        return total

    def hedge_recognition(
        self,
        signals,
    ):
        hedges = []
        directional = []

        for signal in signals:
            trade_type = str(
                signal.get(
                    "trade_type",
                    ""
                )
            ).upper()

            if "HEDGE" in trade_type:
                hedges.append(signal)
            else:
                directional.append(signal)

        return {
            "hedges": hedges,
            "directional": directional,
        }

    def correlated_overlap(
        self,
        signals,
        correlation_groups,
    ):
        """
        correlation_groups:
            {
                "INDEX": ["NIFTY", "BANKNIFTY"]
            }
        """

        exposure = {}

        for bucket, symbols in correlation_groups.items():
            bucket_hits = []

            for signal in signals:
                symbol = str(
                    signal.get(
                        "symbol",
                        ""
                    )
                )

                if symbol in symbols:
                    bucket_hits.append(symbol)

            if len(bucket_hits) > 1:
                exposure[bucket] = bucket_hits

        return exposure


exposure_governor = ExposureGovernor()