from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolCollision:
    symbol_name: str
    primary_module: str
    conflicting_module: str