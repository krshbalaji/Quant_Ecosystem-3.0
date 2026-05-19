from dataclasses import dataclass
from .base_profile import BaseProfile


@dataclass
class FNOProfile(BaseProfile):
    name: str = "FNO"
    risk_per_trade: float = 1.00
    daily_risk_budget: float = 2.50
    max_open_positions: int = 4
    max_consecutive_losses: int = 5
    cooldown_after_loss_minutes: int = 60
    cooldown_after_win_minutes: int = 30
    min_score_threshold: int = 70
    session_rules: str = "momentum-driven range capture; manage gamma risk"
    execution_style: str = "active; strike-aware"
    allow_pyramiding: bool = True
    allow_averaging: bool = False
    allow_partial_exit: bool = True
    allow_trailing: bool = True
    time_horizon: str = "SHORT_TO_MEDIUM"
    correlation_group: str = "FNO"
