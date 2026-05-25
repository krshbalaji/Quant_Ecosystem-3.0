class PortfolioOptimizer:

    def equal_weight(
        self,
        symbols,
        total_capital,
    ):
        if not symbols:
            return {}

        allocation = (
            float(total_capital)
            / len(symbols)
        )

        return {
            s: allocation
            for s in symbols
        }

    def target_weight_allocate(
        self,
        total_capital,
        target_weights,
    ):
        result = {}

        for symbol, weight in (
            target_weights.items()
        ):
            result[symbol] = (
                float(total_capital)
                * float(weight)
            )

        return result

    def rebalance_orders(
        self,
        current_allocations,
        target_allocations,
    ):
        orders = {}

        symbols = set(
            current_allocations.keys()
        ) | set(
            target_allocations.keys()
        )

        for symbol in symbols:
            current = float(
                current_allocations.get(
                    symbol,
                    0.0,
                )
            )

            target = float(
                target_allocations.get(
                    symbol,
                    0.0,
                )
            )

            delta = target - current

            if delta != 0:
                orders[symbol] = delta

        return orders

    def risk_parity_allocate(
        self,
        total_capital,
        volatility_map,
    ):
        if not volatility_map:
            return {}

        inverse_vol = {}

        for symbol, vol in (
            volatility_map.items()
        ):
            vol = float(vol)

            if vol <= 0:
                continue

            inverse_vol[symbol] = (
                1.0 / vol
            )

        total_inverse = sum(
            inverse_vol.values()
        )

        if total_inverse == 0:
            return {}

        result = {}

        for symbol, inv in (
            inverse_vol.items()
        ):
            weight = inv / total_inverse

            result[symbol] = (
                float(total_capital)
                * weight
            )

        return result

    def capital_efficiency_score(
        self,
        expected_return,
        risk,
    ):
        risk = float(risk)

        if risk <= 0:
            return 0.0

        return (
            float(expected_return)
            / risk
        )


portfolio_optimizer = (
    PortfolioOptimizer()
)