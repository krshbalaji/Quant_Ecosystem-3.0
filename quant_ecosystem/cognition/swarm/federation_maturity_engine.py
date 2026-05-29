from .federation_maturity_registry import (
    FederationMaturityRegistry,
)
from .maturity_level import (
    MaturityLevel,
)
from .maturity_report import (
    MaturityReport,
)


class FederationMaturityEngine:

    def evaluate(
        self,
        registry: FederationMaturityRegistry,
    ) -> MaturityReport:

        count = registry.count()

        if count >= 20:
            level = MaturityLevel.SOVEREIGN
        elif count >= 10:
            level = MaturityLevel.INSTITUTIONAL
        elif count >= 5:
            level = MaturityLevel.OPERATIONAL
        elif count >= 2:
            level = MaturityLevel.DEVELOPING
        else:
            level = MaturityLevel.EMERGING

        return MaturityReport(
            assessed_domains=count,
            maturity_level=level,
        )