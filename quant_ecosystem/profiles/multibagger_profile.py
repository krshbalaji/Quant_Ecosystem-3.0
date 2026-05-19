from dataclasses import dataclass
from .base_profile import BaseProfile


@dataclass
class MultibaggerProfile(BaseProfile):
    name: str = "MULTIBAGGER"
    risk_per_trade: float = 1.50
    daily_risk_budget: float = 3.00
    max_open_positions: int = 5
    max_consecutive_losses: int = 7
    cooldown_after_loss_minutes: int = 180
    cooldown_after_win_minutes: int = 120
    min_score_threshold: int = 68
    session_rules: str = "long-term alpha capture; limited position turnover"
    execution_style: str = "patient; target rich setups"
    allow_pyramiding: bool = True
    allow_averaging: bool = True
    allow_partial_exit: bool = False
    allow_trailing: bool = True
    time_horizon: str = "LONG_TERM"
    correlation_group: str = "MULTIBAGGER"
