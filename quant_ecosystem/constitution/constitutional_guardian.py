class ConstitutionalGuardian:

    def enforce(
        self,
        *,
        constitutional,
    ):

        if not constitutional:

            raise RuntimeError(
                "Constitutional violation detected"
            )


constitutional_guardian = (
    ConstitutionalGuardian()
)