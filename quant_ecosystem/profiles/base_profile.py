from dataclasses import dataclass


@dataclass
class BaseProfile:
    name: str = "BASE"
    risk_per_trade: float = 0.0
    daily_risk_budget: float = 0.0
    max_open_positions: int = 0
    max_consecutive_losses: int = 0
    cooldown_after_loss_minutes: int = 0
    cooldown_after_win_minutes: int = 0
    min_score_threshold: int = 0
    session_rules: str = ""
    execution_style: str = ""
    allow_pyramiding: bool = False
    allow_averaging: bool = False
    allow_partial_exit: bool = False
    allow_trailing: bool = False
    time_horizon: str = ""
    correlation_group: str = "GENERAL"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "risk_per_trade": self.risk_per_trade,
            "daily_risk_budget": self.daily_risk_budget,
            "max_open_positions": self.max_open_positions,
            "max_consecutive_losses": self.max_consecutive_losses,
            "cooldown_after_loss_minutes": self.cooldown_after_loss_minutes,
            "cooldown_after_win_minutes": self.cooldown_after_win_minutes,
            "min_score_threshold": self.min_score_threshold,
            "session_rules": self.session_rules,
            "execution_style": self.execution_style,
            "allow_pyramiding": self.allow_pyramiding,
            "allow_averaging": self.allow_averaging,
            "allow_partial_exit": self.allow_partial_exit,
            "allow_trailing": self.allow_trailing,
            "time_horizon": self.time_horizon,
            "correlation_group": self.correlation_group,
        }
