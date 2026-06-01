from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .optimization_candidate import (
    OptimizationCandidate,
)


class FederationOptimizationRegistry(
    AppendRegistry[
        OptimizationCandidate
    ]
):

    def candidates(
        self,
    ) -> list[
        OptimizationCandidate
    ]:

        return self.entries()