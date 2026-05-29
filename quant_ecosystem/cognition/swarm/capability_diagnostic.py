from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDiagnostic:
    capability_id: str
    status: str