from dataclasses import dataclass


@dataclass(frozen=True)
class RouterAdapterContract:
    adapter_id: str
    target_router: str
    enabled: bool = True