class IdentityGuardian:

    def stable(
        self,
        *,
        consistency_score,
    ):

        return consistency_score >= 0.20


identity_guardian = (
    IdentityGuardian()
)