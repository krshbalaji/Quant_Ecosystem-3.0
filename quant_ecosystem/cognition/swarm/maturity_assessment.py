from dataclasses import dataclass

from .maturity_level import (
    MaturityLevel,
)


@dataclass(frozen=True)
class MaturityAssessment:
    domain: str
    maturity_level: MaturityLevel