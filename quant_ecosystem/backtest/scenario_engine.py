class ScenarioEngine:

    def crash(
        self,
        pnl_series,
        crash_factor=0.50,
    ):
        return [
            pnl * crash_factor
            for pnl in pnl_series
        ]

    def gap_down(
        self,
        pnl_series,
        gap_factor=0.70,
    ):
        stressed = []

        for pnl in pnl_series:
            if pnl > 0:
                stressed.append(
                    pnl * gap_factor
                )
            else:
                stressed.append(
                    pnl * 1.25
                )

        return stressed

    def gap_up(
        self,
        pnl_series,
        boost_factor=1.20,
    ):
        stressed = []

        for pnl in pnl_series:
            if pnl > 0:
                stressed.append(
                    pnl * boost_factor
                )
            else:
                stressed.append(pnl)

        return stressed

    def volatility_spike(
        self,
        pnl_series,
        vol_factor=1.50,
    ):
        return [
            pnl * vol_factor
            for pnl in pnl_series
        ]

    def scenario_snapshot(
        self,
        pnl_series,
    ):
        return {
            "total_pnl": sum(pnl_series),
            "worst_trade": min(pnl_series),
            "best_trade": max(pnl_series),
            "trades": len(pnl_series),
        }

    def run(
        self,
        pnl_series,
    ):
        return {
            "crash": self.scenario_snapshot(
                self.crash(pnl_series)
            ),
            "gap_down": self.scenario_snapshot(
                self.gap_down(pnl_series)
            ),
            "gap_up": self.scenario_snapshot(
                self.gap_up(pnl_series)
            ),
            "volatility_spike": (
                self.scenario_snapshot(
                    self.volatility_spike(
                        pnl_series
                    )
                )
            ),
        }


scenario_engine = ScenarioEngine()