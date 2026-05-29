from dataclasses import dataclass

from .maturity_level import (
    MaturityLevel,
)


@dataclass(frozen=True)
class MaturityReport:
    assessed_domains: int
    maturity_level: MaturityLevel