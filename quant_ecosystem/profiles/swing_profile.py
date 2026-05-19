from dataclasses import dataclass
from .base_profile import BaseProfile


@dataclass
class SwingProfile(BaseProfile):
    name: str = "SWING"
    risk_per_trade: float = 0.75
    daily_risk_budget: float = 1.50
    max_open_positions: int = 3
    max_consecutive_losses: int = 4
    cooldown_after_loss_minutes: int = 120
    cooldown_after_win_minutes: int = 60
    min_score_threshold: int = 75
    session_rules: str = "multi-day positioning; wider stops allowed"
    execution_style: str = "patient; trend-oriented"
    allow_pyramiding: bool = True
    allow_averaging: bool = True
    allow_partial_exit: bool = True
    allow_trailing: bool = True
    time_horizon: str = "MEDIUM_TERM"
    correlation_group: str = "SWING"
