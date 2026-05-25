from dataclasses import dataclass, field


@dataclass
class ApiRequest:
    endpoint: str
    action: str = ""
    payload: dict = field(
        default_factory=dict
    )


@dataclass
class ApiResponse:
    success: bool
    payload: dict = field(
        default_factory=dict
    )