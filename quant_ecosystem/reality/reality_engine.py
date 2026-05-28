from quant_ecosystem.reality.reality_snapshot import (
    RealitySnapshot,
)

from quant_ecosystem.reality.anomaly_detector import (
    anomaly_detector,
)


class RealityEngine:

    def snapshot(
        self,
        *,
        broker_health,
        liquidity,
        volatility,
    ):

        anomaly = (
            anomaly_detector
            .anomaly_score(
                broker_health=(
                    broker_health
                ),
                liquidity=(
                    liquidity
                ),
                volatility=(
                    volatility
                ),
            )
        )

        return (
            RealitySnapshot(
                broker_health=(
                    broker_health
                ),
                liquidity=liquidity,
                volatility=(
                    volatility
                ),
                anomaly_score=(
                    anomaly
                ),
            )
        )


reality_engine = (
    RealityEngine()
)