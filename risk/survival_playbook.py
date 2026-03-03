from core.config_loader import Config
from utils.decimal_utils import quantize


class SurvivalPlaybook:

    def __init__(self):
        self.config = Config()
        self.mode = "NORMAL"
        self.skip_streak = 0
        self.last_action = "NONE"
        self._last_defensive_reason = ""

    def evaluate(self, router, cycle_result, intelligence_report):
        reason = str(cycle_result.get("reason", ""))
        traded = cycle_result.get("status") == "TRADE"
        regime_adv = str(intelligence_report.get("regime_advanced", "")).upper()

        if traded:
            self.skip_streak = 0
        elif reason in {
            "MAX_STRATEGY_EXPOSURE",
            "MAX_PORTFOLIO_EXPOSURE",
            "MAX_SYMBOL_EXPOSURE",
            "MAX_SECTOR_EXPOSURE",
            "MAX_ASSET_EXPOSURE",
        }:
            self.skip_streak += 1
        else:
            self.skip_streak = max(0, self.skip_streak - 1)

        if regime_adv in {"PANIC", "BREAKOUT"}:
            return {"action": "PAUSE", "reason": f"SURVIVAL_{regime_adv}"}

        if router.state.daily_drawdown >= (0.75 * router.risk_engine.max_daily_dd):
            return {"action": "DEFENSIVE", "reason": "SURVIVAL_DRAWDOWN_PRESSURE"}

        if router.state.consecutive_losses >= max(3, self.config.cooldown_after_loss + 1):
            return {"action": "DEFENSIVE", "reason": "SURVIVAL_LOSS_STREAK"}

        if self.skip_streak >= 8:
            return {"action": "DEFENSIVE", "reason": "SURVIVAL_PERSISTENT_RISK_BLOCK"}

        return {"action": "NORMAL", "reason": "SURVIVAL_STABLE"}

    def apply(self, router, control_center, decision):
        action = decision.get("action", "NORMAL")
        reason = decision.get("reason", "SURVIVAL_UNKNOWN")

        if action == "PAUSE":
            router.stop_trading()
            router.set_auto_mode(False)
            control_center.execute("close_all", router)
            self.mode = "PAUSED"
            router.survival_mode = self.mode
            self.last_action = reason
            return f"{reason}: trading paused and exposure close initiated."

        if action == "DEFENSIVE":
            if self.mode == "DEFENSIVE":
                return None
            # Tighten risk and shrink tradable set in survival mode.
            new_risk = router.risk_engine.set_trade_risk_pct(router.risk_engine.max_trade_risk * 0.85)
            router.symbols = list(router.symbols[:3])
            self.mode = "DEFENSIVE"
            router.survival_mode = self.mode
            self.last_action = reason
            self._last_defensive_reason = reason
            return f"{reason}: risk reduced to {quantize(new_risk, 4)} and symbols limited to {len(router.symbols)}."

        if action == "NORMAL" and self.mode == "DEFENSIVE":
            # Controlled recovery path.
            restored = router.risk_engine.set_trade_risk_pct(min(router.risk_engine.base_trade_risk, router.risk_engine.max_trade_risk * 1.05))
            self.mode = "NORMAL"
            router.survival_mode = self.mode
            self.last_action = "SURVIVAL_RECOVERY"
            return f"SURVIVAL_RECOVERY: risk normalized to {quantize(restored, 4)}."

        self.last_action = reason
        return None
