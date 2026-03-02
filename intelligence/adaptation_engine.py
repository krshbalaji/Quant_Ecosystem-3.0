from utils.decimal_utils import quantize


class AdaptationEngine:

    def apply(self, state, risk_engine):
        trades = state.trade_history
        if not trades:
            return {
                "action": "HOLD",
                "new_trade_risk_pct": quantize(risk_engine.max_trade_risk, 4),
                "reason": "No trades in session.",
            }

        pnl_values = [float(item.get("cycle_pnl", 0.0)) for item in trades[-50:]]
        wins = [p for p in pnl_values if p > 0]
        win_rate = (len(wins) / len(pnl_values)) * 100.0 if pnl_values else 0.0
        expectancy = sum(pnl_values) / len(pnl_values) if pnl_values else 0.0

        current = risk_engine.max_trade_risk
        target = current
        action = "HOLD"
        reason = "Performance within control band."

        if state.total_drawdown_pct > (0.5 * risk_engine.max_daily_dd) or expectancy < 0:
            target = current * 0.9
            action = "DECREASE_RISK"
            reason = "Drawdown/expectancy deterioration detected."
        elif win_rate >= 58 and expectancy > 0 and state.total_drawdown_pct < 1.0:
            target = current * 1.05
            action = "INCREASE_RISK"
            reason = "Stable edge with controlled drawdown."

        new_value = risk_engine.set_trade_risk_pct(target)
        return {
            "action": action,
            "new_trade_risk_pct": quantize(new_value, 4),
            "win_rate_pct": quantize(win_rate, 4),
            "expectancy_abs": quantize(expectancy, 4),
            "reason": reason,
        }
