from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationTarget:
    category_name: str