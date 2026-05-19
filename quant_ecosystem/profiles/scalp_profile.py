from dataclasses import dataclass
from .base_profile import BaseProfile


@dataclass
class ScalpProfile(BaseProfile):
    name: str = "SCALP"
    risk_per_trade: float = 0.20
    daily_risk_budget: float = 0.60
    max_open_positions: int = 1
    max_consecutive_losses: int = 2
    cooldown_after_loss_minutes: int = 45
    cooldown_after_win_minutes: int = 15
    min_score_threshold: int = 88
    session_rules: str = "strict anti-chase; limit to high-probability setups"
    execution_style: str = "fast; tight execution"
    allow_pyramiding: bool = False
    allow_averaging: bool = False
    allow_partial_exit: bool = True
    allow_trailing: bool = True
    time_horizon: str = "SHORT_TERM"
    correlation_group: str = "SCALP"
