from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .trust_metric import (
    TrustMetric,
)


class FederationTrustRegistry(
    AppendRegistry[
        TrustMetric
    ]
):

    def metrics(
        self,
    ) -> list[TrustMetric]:

        return self.entries()