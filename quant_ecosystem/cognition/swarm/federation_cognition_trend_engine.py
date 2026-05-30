from .federation_cognition_trend_point import (
    FederationCognitionTrendPoint,
)
from .federation_cognition_trend_report import (
    FederationCognitionTrendReport,
)


class FederationCognitionTrendEngine:

    def evaluate(
        self,
        points: list[
            FederationCognitionTrendPoint
        ],
    ) -> FederationCognitionTrendReport:

        if len(points) < 2:
            return FederationCognitionTrendReport(
                direction="STABLE",
                change_rate=0.0,
                sample_count=len(points),
            )

        earliest = points[0]
        latest = points[-1]

        change_rate = (
            latest.cognition_index
            - earliest.cognition_index
        )

        if change_rate > 0:
            direction = "IMPROVING"
        elif change_rate < 0:
            direction = "DECLINING"
        else:
            direction = "STABLE"

        return FederationCognitionTrendReport(
            direction=direction,
            change_rate=change_rate,
            sample_count=len(points),
        )