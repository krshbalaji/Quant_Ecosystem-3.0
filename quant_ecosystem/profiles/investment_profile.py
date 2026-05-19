from dataclasses import dataclass
from .base_profile import BaseProfile


@dataclass
class InvestmentProfile(BaseProfile):
    name: str = "INVESTMENT"
    risk_per_trade: float = 2.50
    daily_risk_budget: float = 5.00
    max_open_positions: int = 8
    max_consecutive_losses: int = 10
    cooldown_after_loss_minutes: int = 240
    cooldown_after_win_minutes: int = 180
    min_score_threshold: int = 65
    session_rules: str = "portfolio-style investing; low churn"
    execution_style: str = "patient; entry budgeted"
    allow_pyramiding: bool = True
    allow_averaging: bool = True
    allow_partial_exit: bool = False
    allow_trailing: bool = True
    time_horizon: str = "VERY_LONG_TERM"
    correlation_group: str = "INVESTMENT"
