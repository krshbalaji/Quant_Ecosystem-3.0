from .federation_risk_registry import (
    FederationRiskRegistry,
)
from .risk_report import (
    RiskReport,
)


class FederationRiskEngine:

    def evaluate(
        self,
        registry: FederationRiskRegistry,
    ) -> RiskReport:

        indicators = (
            registry.indicators()
        )

        if not indicators:

            return RiskReport(
                highest_risk_category="none",
                highest_risk_score=0.0,
            )

        highest = max(
            indicators,
            key=lambda x: x.risk_score,
        )

        return RiskReport(
            highest_risk_category=(
                highest.category_name
            ),
            highest_risk_score=(
                highest.risk_score
            ),
        )