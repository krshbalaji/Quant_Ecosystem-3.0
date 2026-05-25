from dataclasses import dataclass, field


@dataclass
class RuntimeConfig:
    environment: str
    broker: str
    mode: str
    risk_enabled: bool = True
    telemetry_enabled: bool = True
    metadata: dict = field(default_factory=dict)