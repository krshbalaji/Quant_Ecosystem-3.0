from dataclasses import dataclass


@dataclass
class ConstitutionalLaw:

    law_name: str

    immutable: bool

    enabled: bool