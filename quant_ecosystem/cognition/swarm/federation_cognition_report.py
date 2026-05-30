from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionReport:
    cognition_index: float
    strongest_dimension: str
    weakest_dimension: str