from .federation_cognition_forecast_report import (
    FederationCognitionForecastReport,
)
from .federation_cognition_alert_report import (
    FederationCognitionAlertReport,
)


class FederationCognitionAlertEngine:

    def evaluate(
        self,
        forecast: FederationCognitionForecastReport,
    ) -> FederationCognitionAlertReport:

        if forecast.projected_index < 0.25:
            level = "CRITICAL_DECLINE_ALERT"

        elif forecast.direction == "DECLINING":
            level = "DECLINING_ALERT"

        elif forecast.direction == "IMPROVING":
            level = "IMPROVING_ALERT"

        else:
            level = "STABLE_ALERT"

        return FederationCognitionAlertReport(
            level=level,
            alert_count=1,
        )