from dataclasses import dataclass, field
from typing import List

from .audit_event import AuditEvent
from quant_ecosystem.core.multimap_store import MultiMapStore


@dataclass
class ExecutionLineage:
    lineage_id: str
    events: List[AuditEvent] = field(default_factory=list)

    def __post_init__(self):
        # shadow multimap store for migration parity (writes only)
        try:
            self._shadow_store = MultiMapStore()
        except Exception:
            self._shadow_store = None

    def append(
        self,
        event: AuditEvent,
    ) -> None:
        # legacy write (primary)
        self.events.append(event)

        # shadow write to MultiMapStore for parity
        if getattr(self, "_shadow_store", None) is not None:
            try:
                self._shadow_store.put(self.lineage_id, event)
            except Exception:
                # swallow to avoid changing behavior
                pass

    def count(self) -> int:
        return len(self.events)
