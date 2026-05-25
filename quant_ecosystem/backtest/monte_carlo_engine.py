import random


class MonteCarloEngine:

    def shuffled_series(
        self,
        pnl_series,
    ):
        cloned = list(pnl_series)

        random.shuffle(cloned)

        return cloned

    def equity_curve(
        self,
        pnl_series,
        starting_equity=100000,
    ):
        curve = [starting_equity]

        current = starting_equity

        for pnl in pnl_series:
            current += pnl
            curve.append(current)

        return curve

    def max_drawdown(
        self,
        equity_curve,
    ):
        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value

            dd = peak - value

            if dd > max_dd:
                max_dd = dd

        return max_dd

    def simulate(
        self,
        pnl_series,
        iterations=100,
        starting_equity=100000,
    ):
        results = []

        for _ in range(iterations):
            shuffled = self.shuffled_series(
                pnl_series
            )

            curve = self.equity_curve(
                shuffled,
                starting_equity,
            )

            results.append(
                {
                    "final_equity": curve[-1],
                    "max_drawdown": (
                        self.max_drawdown(
                            curve
                        )
                    ),
                }
            )

        return results

    def robustness_snapshot(
        self,
        simulation_results,
    ):
        if not simulation_results:
            return {
                "iterations": 0,
                "avg_final_equity": 0.0,
                "worst_drawdown": 0.0,
                "best_final_equity": 0.0,
            }

        finals = [
            x["final_equity"]
            for x in simulation_results
        ]

        dds = [
            x["max_drawdown"]
            for x in simulation_results
        ]

        return {
            "iterations": len(
                simulation_results
            ),
            "avg_final_equity": (
                sum(finals)
                / len(finals)
            ),
            "worst_drawdown": max(dds),
            "best_final_equity": max(finals),
        }

    def run(
        self,
        pnl_series,
        iterations=100,
        starting_equity=100000,
    ):
        sims = self.simulate(
            pnl_series,
            iterations=iterations,
            starting_equity=starting_equity,
        )

        snapshot = (
            self.robustness_snapshot(
                sims
            )
        )

        return {
            "simulations": sims,
            "snapshot": snapshot,
        }


monte_carlo_engine = (
    MonteCarloEngine()
)