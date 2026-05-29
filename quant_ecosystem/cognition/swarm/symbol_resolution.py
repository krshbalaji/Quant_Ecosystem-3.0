from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolResolution:
    symbol_name: str
    canonical_module: str