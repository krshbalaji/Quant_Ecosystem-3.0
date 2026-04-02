from dataclasses import dataclass

@dataclass
class LoopConfig:
    cycle_interval_sec: int = 120
    discovery_batch: int = 20
    mutation_batch: int = 10
    promote_top_n: int = 5
    promote_threshold: float = 0.45