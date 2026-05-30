from .federation_cognition_alert_report import (
    FederationCognitionAlertReport,
)
from .federation_cognition_response_report import (
    FederationCognitionResponseReport,
)


class FederationCognitionResponseEngine:

    def evaluate(
        self,
        alert: FederationCognitionAlertReport,
    ) -> FederationCognitionResponseReport:

        mapping = {
            "CRITICAL_DECLINE_ALERT":
                "EXECUTE_STABILIZATION_PLAN",
            "DECLINING_ALERT":
                "EXECUTE_IMPROVEMENT_PLAN",
            "IMPROVING_ALERT":
                "ACCELERATE_STRATEGIC_GROWTH",
            "STABLE_ALERT":
                "MAINTAIN_CURRENT_STATE",
        }

        action = mapping.get(
            alert.level,
            "REVIEW_REQUIRED",
        )

        return FederationCognitionResponseReport(
            recommended_action=action,
            response_count=1,
        )