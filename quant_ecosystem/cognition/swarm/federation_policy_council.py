from .constitutional_policy_engine import (
    ConstitutionalPolicyEngine,
)
from .federation_policy import FederationPolicy
from .governance_enforcement_record import (
    GovernanceEnforcementRecord,
)


class FederationPolicyCouncil:

    def __init__(self):
        self.engine = ConstitutionalPolicyEngine()

    def enforce(
        self,
        policy: FederationPolicy,
        confidence: float,
    ) -> GovernanceEnforcementRecord:

        violation = self.engine.evaluate(
            policy,
            confidence,
        )

        if violation is None:
            return GovernanceEnforcementRecord(
                policy_id=policy.policy_id,
                outcome="approved",
                compliant=True,
            )

        return GovernanceEnforcementRecord(
            policy_id=policy.policy_id,
            outcome="rejected",
            compliant=False,
        )