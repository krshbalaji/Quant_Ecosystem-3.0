"""Risk micro-layer adapter."""


class RiskEngineLayer:
    """Non-invasive facade for exposure and drawdown telemetry."""

    def __init__(self, risk_engine=None):
        self.risk_engine = risk_engine

    def limits(self):
        if not self.risk_engine:
            return {}
        return {
            "max_trade_risk_pct": float(getattr(self.risk_engine, "max_trade_risk", 0.0)),
            "max_daily_loss_pct": float(getattr(self.risk_engine, "max_daily_loss_pct", 0.0)),
            "hard_drawdown_limit_pct": float(getattr(self.risk_engine, "hard_drawdown_limit_pct", 0.0)),
        }
