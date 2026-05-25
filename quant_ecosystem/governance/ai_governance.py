class AIGovernance:

    def evaluate(
        self,
        model_payload,
        decision_payload,
    ):
        if not model_payload:
            return {
                "approved": False,
                "reason": "MODEL_NOT_REGISTERED",
            }

        if not model_payload["active"]:
            return {
                "approved": False,
                "reason": "MODEL_INACTIVE",
            }

        if decision_payload.get(
            "risk_level"
        ) == "PROHIBITED":
            return {
                "approved": False,
                "reason": "POLICY_BLOCK",
            }

        return {
            "approved": True,
            "reason": "APPROVED",
        }


ai_governance = AIGovernance()