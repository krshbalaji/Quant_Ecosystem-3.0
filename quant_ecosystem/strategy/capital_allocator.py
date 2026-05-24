class CapitalAllocator:

    def fixed_bucket(
        self,
        total_capital,
        allocations,
    ):
        """
        allocations:
            {
                "strategy_a": 0.25,
                "strategy_b": 0.50,
            }
        """

        result = {}

        total_capital = float(total_capital)

        for strategy_id, weight in allocations.items():
            result[strategy_id] = (
                total_capital
                * float(weight)
            )

        return result

    def proportional_weights(
        self,
        total_capital,
        strategy_scores,
    ):
        if not strategy_scores:
            return {}

        total_score = sum(
            float(v)
            for v in strategy_scores.values()
        )

        if total_score <= 0:
            return {}

        result = {}

        for strategy_id, score in strategy_scores.items():
            result[strategy_id] = (
                total_capital
                * (float(score) / total_score)
            )

        return result

    def volatility_targeted(
        self,
        total_capital,
        strategy_vols,
    ):
        """
        Lower volatility gets larger allocation.
        """

        inverse = {}

        for strategy_id, vol in strategy_vols.items():
            vol = float(vol)

            if vol <= 0:
                continue

            inverse[strategy_id] = 1.0 / vol

        return self.proportional_weights(
            total_capital,
            inverse,
        )

    def drawdown_throttle(
        self,
        allocation,
        current_drawdown,
        threshold=0.10,
        throttle_factor=0.50,
    ):
        allocation = float(allocation)

        if float(current_drawdown) >= threshold:
            return allocation * throttle_factor

        return allocation

    def enforce_max_cap(
        self,
        allocations,
        max_pct,
        total_capital,
    ):
        capped = {}
        max_amt = (
            float(total_capital)
            * float(max_pct)
        )

        for strategy_id, amount in allocations.items():
            capped[strategy_id] = min(
                float(amount),
                max_amt,
            )

        return capped

    def adaptive_rebalance(
        self,
        total_capital,
        strategy_scores,
        drawdowns=None,
        max_pct=0.40,
    ):
        allocations = self.proportional_weights(
            total_capital,
            strategy_scores,
        )

        if drawdowns:
            adjusted = {}

            for strategy_id, amount in allocations.items():
                dd = float(
                    drawdowns.get(
                        strategy_id,
                        0.0,
                    )
                )

                adjusted[strategy_id] = (
                    self.drawdown_throttle(
                        amount,
                        dd,
                    )
                )

            allocations = adjusted

        allocations = self.enforce_max_cap(
            allocations,
            max_pct,
            total_capital,
        )

        return allocations


capital_allocator = CapitalAllocator()