from quant_ecosystem.constitution.constitution_registry import (
    constitution_registry,
)


class ConstitutionEngine:

    def compliant(
        self,
        *,
        existential_probability,
        anomaly_score,
    ):

        laws = (
            constitution_registry
            .laws()
        )

        for law in laws:

            if (
                law.law_name
                == "NO_EXISTENTIAL_RISK"
            ):

                if (
                    existential_probability
                    >= 0.75
                ):
                    return False

            if (
                law.law_name
                == "NO_FALSE_EXECUTION"
            ):

                if anomaly_score >= 0.80:
                    return False

        return True


constitution_engine = (
    ConstitutionEngine()
)