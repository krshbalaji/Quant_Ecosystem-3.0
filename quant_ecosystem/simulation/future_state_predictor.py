from quant_ecosystem.simulation.simulation_engine import (
    simulation_engine,
)


class FutureStatePredictor:

    def predict(
        self,
        *,
        volatility,
        liquidity,
        broker_health,
    ):

        return (
            simulation_engine
            .simulate(
                volatility=(
                    volatility
                ),
                liquidity=(
                    liquidity
                ),
                broker_health=(
                    broker_health
                ),
            )
        )


future_state_predictor = (
    FutureStatePredictor()
)