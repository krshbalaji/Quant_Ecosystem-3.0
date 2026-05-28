from quant_ecosystem.constitution.constitutional_law import (
    ConstitutionalLaw,
)


class ConstitutionRegistry:

    def __init__(self):

        self._laws = [
            ConstitutionalLaw(
                law_name=(
                    "SURVIVAL_FIRST"
                ),
                immutable=True,
                enabled=True,
            ),
            ConstitutionalLaw(
                law_name=(
                    "NO_FALSE_EXECUTION"
                ),
                immutable=True,
                enabled=True,
            ),
            ConstitutionalLaw(
                law_name=(
                    "NO_EXISTENTIAL_RISK"
                ),
                immutable=True,
                enabled=True,
            ),
        ]

    def laws(self):

        return list(
            self._laws
        )


constitution_registry = (
    ConstitutionRegistry()
)