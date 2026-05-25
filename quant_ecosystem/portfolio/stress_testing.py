class PortfolioStressTesting:

    def crash_simulation(
        self,
        positions,
        crash_pct,
    ):
        crash_pct = float(crash_pct)

        total_loss = 0.0

        for pos in positions:
            mv = float(
                pos.get(
                    "market_value",
                    0.0,
                )
            )

            total_loss += (
                mv * crash_pct / 100.0
            )

        return total_loss

    def volatility_shock(
        self,
        option_positions,
        vol_expansion_pct,
    ):
        shock = float(
            vol_expansion_pct
        ) / 100.0

        pnl = 0.0

        for pos in option_positions:
            vega = float(
                pos.get("vega", 0.0)
            )

            qty = float(
                pos.get("qty", 0)
            )

            pnl += (
                vega * qty * shock
            )

        return pnl

    def gap_risk(
        self,
        positions,
        gap_pct,
    ):
        gap_pct = float(gap_pct)

        pnl = 0.0

        for pos in positions:
            mv = float(
                pos.get(
                    "market_value",
                    0.0,
                )
            )

            pnl += (
                mv * gap_pct / 100.0
            )

        return pnl

    def liquidity_haircut(
        self,
        positions,
        haircut_pct,
    ):
        haircut_pct = float(
            haircut_pct
        )

        adjusted = []

        for pos in positions:
            mv = float(
                pos.get(
                    "market_value",
                    0.0,
                )
            )

            stressed = mv * (
                1
                - haircut_pct / 100.0
            )

            adjusted.append(
                {
                    **pos,
                    "stressed_value": stressed,
                }
            )

        return adjusted

    def scenario_matrix(
        self,
        positions,
    ):
        return {
            "market_crash_10": (
                self.crash_simulation(
                    positions,
                    -10,
                )
            ),
            "market_crash_20": (
                self.crash_simulation(
                    positions,
                    -20,
                )
            ),
            "gap_down_5": (
                self.gap_risk(
                    positions,
                    -5,
                )
            ),
            "liquidity_haircut_15": (
                self.liquidity_haircut(
                    positions,
                    15,
                )
            ),
        }


portfolio_stress_testing = (
    PortfolioStressTesting()
)