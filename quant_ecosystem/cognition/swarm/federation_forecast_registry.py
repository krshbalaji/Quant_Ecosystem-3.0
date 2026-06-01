from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .forecast_projection import (
    ForecastProjection,
)


class FederationForecastRegistry(
    AppendRegistry[
        ForecastProjection
    ]
):

    def forecasts(
        self,
    ) -> list[
        ForecastProjection
    ]:

        return self.entries()