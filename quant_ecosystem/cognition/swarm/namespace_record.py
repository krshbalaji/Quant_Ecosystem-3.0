from dataclasses import dataclass


@dataclass(frozen=True)
class NamespaceRecord:
    symbol_name: str
    module_name: str