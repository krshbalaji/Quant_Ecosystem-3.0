from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .architecture_trend_point import (
    ArchitectureTrendPoint,
)


class FederationTrendRegistry(
    AppendRegistry[
        ArchitectureTrendPoint
    ]
):

    def points(
        self,
    ) -> list[
        ArchitectureTrendPoint
    ]:

        return self.entries()