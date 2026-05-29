from dataclasses import dataclass


@dataclass(frozen=True)
class RouterExecutionResult:
    request_id: str
    accepted: bool
    adapter_id: str