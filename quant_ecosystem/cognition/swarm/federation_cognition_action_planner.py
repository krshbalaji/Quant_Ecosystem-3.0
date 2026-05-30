from .federation_cognition_action_step import (
    FederationCognitionActionStep,
)
from .federation_cognition_action_plan import (
    FederationCognitionActionPlan,
)
from .federation_cognition_response_report import (
    FederationCognitionResponseReport,
)


class FederationCognitionActionPlanner:

    def create_plan(
        self,
        response: FederationCognitionResponseReport,
    ) -> FederationCognitionActionPlan:

        templates = {
            "EXECUTE_STABILIZATION_PLAN": [
                "Assess instability sources",
                "Deploy resilience controls",
                "Monitor recovery",
            ],
            "EXECUTE_IMPROVEMENT_PLAN": [
                "Analyze weak dimensions",
                "Implement improvements",
                "Re-evaluate cognition",
            ],
            "ACCELERATE_STRATEGIC_GROWTH": [
                "Expand successful initiatives",
                "Increase resource allocation",
                "Monitor growth trajectory",
            ],
            "MAINTAIN_CURRENT_STATE": [
                "Continue monitoring",
                "Validate stability",
                "Schedule review",
            ],
        }

        actions = templates.get(
            response.recommended_action,
            ["Manual review required"],
        )

        steps = [
            FederationCognitionActionStep(
                sequence=i + 1,
                description=action,
            )
            for i, action in enumerate(actions)
        ]

        return FederationCognitionActionPlan(
            action=response.recommended_action,
            steps=steps,
        )