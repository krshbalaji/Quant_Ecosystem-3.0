from dataclasses import dataclass


@dataclass(frozen=True)
class SubsystemAdapterResult:
    request_id: str
    accepted: bool
    subsystem_name: str