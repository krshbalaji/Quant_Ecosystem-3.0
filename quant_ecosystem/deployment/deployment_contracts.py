from dataclasses import dataclass


@dataclass
class DeploymentConfig:
    environment: str
    runtime_mode: str