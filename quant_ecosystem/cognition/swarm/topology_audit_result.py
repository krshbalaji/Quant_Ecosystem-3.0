from dataclasses import dataclass


@dataclass(frozen=True)
class TopologyAuditResult:
    total_symbols: int
    duplicate_symbols: int