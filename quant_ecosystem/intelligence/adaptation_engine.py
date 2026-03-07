from quant_ecosystem.utils.decimal_utils import quantize
from quant_ecosystem.core.config_loader import Config


class AdaptationEngine:

    def __init__(self, **kwargs):
        self.config = Config()

    def apply(self, state, risk_engine):
        trades = state.trade_history
        if not trades:
            return {
                "action": "HOLD",
                "new_trade_risk_pct": quantize(risk_engine.max_trade_risk, 4),
                "reason": "No trades in session.",
            }

        sample_trades = trades[-50:]
        closed_realized = [
            float(item.get("realized_pnl", 0.0))
            for item in sample_trades
            if bool(item.get("closed_trade", False)) and abs(float(item.get("realized_pnl", 0.0))) > 0.0
        ]
        realized_values = closed_realized
        mtm_values = [float(item.get("cycle_pnl", 0.0)) for item in sample_trades]
        wins = [p for p in realized_values if p > 0]
        win_rate = (len(wins) / len(realized_values)) * 100.0 if realized_values else 0.0
        expectancy_realized = sum(realized_values) / len(realized_values) if realized_values else 0.0
        expectancy_mtm = sum(mtm_values) / len(mtm_values) if mtm_values else 0.0
        sample_size = len(sample_trades)
        realized_sample_size = len(realized_values)
        has_shadow = any(bool(item.get("shadow_mode", False)) for item in sample_trades)
        stage_set = {str(item.get("strategy_stage", "")).upper() for item in sample_trades}

        current = risk_engine.max_trade_risk
        target = current
        action = "HOLD"
        reason = "Performance within control band."

        if state.total_drawdown_pct > (0.5 * risk_engine.max_daily_dd) or (realized_sample_size >= 5 and expectancy_realized < 0):
            target = current * 0.9
            action = "DECREASE_RISK"
            reason = "Drawdown/realized expectancy deterioration detected."
        elif (
            sample_size >= self.config.min_adaptation_trades
            and realized_sample_size >= max(8, int(self.config.min_adaptation_trades * 0.4))
            and not has_shadow
            and "PAPER_SHADOW" not in stage_set
            and 58 <= win_rate <= 60
            and expectancy_realized > 0
            and state.total_drawdown_pct < 1.0
        ):
            target = current * 1.05
            action = "INCREASE_RISK"
            reason = "Stable edge with controlled drawdown."
        elif sample_size < self.config.min_adaptation_trades:
            reason = f"Insufficient sample for risk increase ({sample_size}/{self.config.min_adaptation_trades})."
        elif realized_sample_size < max(8, int(self.config.min_adaptation_trades * 0.4)):
            reason = f"Insufficient realized closures ({realized_sample_size}) for risk increase."
        elif has_shadow or "PAPER_SHADOW" in stage_set:
            reason = "Shadow mode evidence only; risk increase blocked."

        new_value = risk_engine.set_trade_risk_pct(target)
        return {
            "action": action,
            "new_trade_risk_pct": quantize(new_value, 4),
            "win_rate_pct": quantize(win_rate, 4),
            "expectancy_realized_abs": quantize(expectancy_realized, 4),
            "expectancy_mtm_abs": quantize(expectancy_mtm, 4),
            "sample_size": sample_size,
            "realized_sample_size": realized_sample_size,
            "shadow_sample": has_shadow,
            "reason": reason,
        }
