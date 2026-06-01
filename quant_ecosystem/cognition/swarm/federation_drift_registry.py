from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .architecture_snapshot import (
    ArchitectureSnapshot,
)


class FederationDriftRegistry(
    AppendRegistry[
        ArchitectureSnapshot
    ]
):

    def snapshots(
        self,
    ) -> list[
        ArchitectureSnapshot
    ]:

        return self.entries()