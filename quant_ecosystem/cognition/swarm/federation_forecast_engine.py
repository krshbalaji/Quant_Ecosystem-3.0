from .architecture_forecast_report import (
    ArchitectureForecastReport,
)
from .federation_forecast_registry import (
    FederationForecastRegistry,
)


class FederationForecastEngine:

    def evaluate(
        self,
        registry: FederationForecastRegistry,
    ) -> ArchitectureForecastReport:

        if not registry.projections():

            return (
                ArchitectureForecastReport(
                    projected_growth=0,
                    projected_total=0,
                )
            )

        latest = (
            registry.projections()[-1]
        )

        return ArchitectureForecastReport(
            projected_growth=(
                latest.projected_count
                - latest.current_count
            ),
            projected_total=(
                latest.projected_count
            ),
        )