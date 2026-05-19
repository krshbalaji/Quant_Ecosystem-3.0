from dataclasses import dataclass
from .base_profile import BaseProfile


@dataclass
class IntradayProfile(BaseProfile):
    name: str = "INTRADAY"
    risk_per_trade: float = 0.40
    daily_risk_budget: float = 1.00
    max_open_positions: int = 2
    max_consecutive_losses: int = 3
    cooldown_after_loss_minutes: int = 30
    cooldown_after_win_minutes: int = 20
    min_score_threshold: int = 80
    session_rules: str = "session-aware trade management; avoid late-day chase"
    execution_style: str = "moderate; session-weighted"
    allow_pyramiding: bool = True
    allow_averaging: bool = False
    allow_partial_exit: bool = True
    allow_trailing: bool = True
    time_horizon: str = "INTRADAY"
    correlation_group: str = "INTRADAY"
