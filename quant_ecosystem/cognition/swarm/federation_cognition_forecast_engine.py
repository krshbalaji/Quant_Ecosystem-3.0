from .federation_cognition_trend_report import (
    FederationCognitionTrendReport,
)
from .federation_cognition_forecast_report import (
    FederationCognitionForecastReport,
)


class FederationCognitionForecastEngine:

    def forecast(
        self,
        current_index: float,
        trend: FederationCognitionTrendReport,
        horizon: int = 1,
    ) -> FederationCognitionForecastReport:

        projected_index = (
            current_index
            + (trend.change_rate * horizon)
        )

        if projected_index > current_index:
            direction = "IMPROVING"
        elif projected_index < current_index:
            direction = "DECLINING"
        else:
            direction = "STABLE"

        return FederationCognitionForecastReport(
            current_index=current_index,
            projected_index=projected_index,
            direction=direction,
            horizon=horizon,
        )