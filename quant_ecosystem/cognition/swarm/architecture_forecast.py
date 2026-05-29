from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureForecast:
    projected_component_count: int