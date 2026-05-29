from .architecture_trend_direction import (
    ArchitectureTrendDirection,
)
from .architecture_trend_report import (
    ArchitectureTrendReport,
)
from .federation_trend_registry import (
    FederationTrendRegistry,
)


class FederationTrendEngine:

    def evaluate(
        self,
        registry: FederationTrendRegistry,
    ) -> ArchitectureTrendReport:

        points = registry.points()

        if len(points) < 2:
            return ArchitectureTrendReport(
                trend_direction=(
                    ArchitectureTrendDirection.STABLE
                ),
                net_change=0,
            )

        change = (
            points[-1].component_count
            - points[0].component_count
        )

        if change > 0:
            direction = (
                ArchitectureTrendDirection.GROWING
            )
        elif change < 0:
            direction = (
                ArchitectureTrendDirection.DECLINING
            )
        else:
            direction = (
                ArchitectureTrendDirection.STABLE
            )

        return ArchitectureTrendReport(
            trend_direction=direction,
            net_change=change,
        )