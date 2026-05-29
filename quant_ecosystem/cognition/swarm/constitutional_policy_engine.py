from typing import Optional

from .federation_policy import FederationPolicy
from .policy_violation import PolicyViolation


class ConstitutionalPolicyEngine:

    def evaluate(
        self,
        policy: FederationPolicy,
        confidence: float,
    ) -> Optional[PolicyViolation]:

        if not policy.active:
            return None

        if confidence >= policy.minimum_confidence:
            return None

        return PolicyViolation(
            policy_id=policy.policy_id,
            reason="confidence_below_threshold",
        )