class AdaptivePolicyEngine:

    def evaluate_policy(
        self,
        decision_payload,
    ):
        risk = decision_payload.get(
            "risk_score",
            0,
        )

        if risk >= 90:
            return {
                "action": "BLOCK",
                "approval_required": True,
            }

        if risk >= 60:
            return {
                "action": "REVIEW",
                "approval_required": True,
            }

        return {
            "action": "ALLOW",
            "approval_required": False,
        }

    def emergency_override(
        self,
        enabled=False,
    ):
        return {
            "override": enabled,
            "action": (
                "FORCE_ALLOW"
                if enabled
                else "NORMAL"
            ),
        }


adaptive_policy_engine = (
    AdaptivePolicyEngine()
)