class SimulationEngine:

    def simulate(
        self,
        *,
        volatility,
        liquidity,
        broker_health,
    ):

        survivability = (
            broker_health
            * liquidity
            * (1.0 - volatility)
        )

        stress_level = (
            volatility
            * (1.0 - liquidity)
        )

        return {
            "survivability": round(
                survivability,
                4,
            ),
            "stress_level": round(
                stress_level,
                4,
            ),
        }


simulation_engine = (
    SimulationEngine()
)