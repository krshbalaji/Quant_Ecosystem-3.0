from core.config_loader import Config
from utils.decimal_utils import quantize


class CapitalGovernanceEngine:

    def __init__(self):
        cfg = Config()
        self.max_strategy_pct = cfg.max_strategy_capital_pct
        self.max_asset_class_pct = cfg.max_asset_class_capital_pct

    def sizing_multiplier(self, trades):
        if not trades:
            return 1.0

        profitable = [t for t in trades if float(t.get("cycle_pnl", 0.0)) > 0]
        recent = trades[-5:]
        recent_losses = [t for t in recent if float(t.get("cycle_pnl", 0.0)) < 0]

        if len(profitable) >= 20:
            return 1.15
        if len(recent_losses) >= 5:
            return 0.70
        return 1.0

    def max_strategy_notional(self, equity):
        return quantize(equity * (self.max_strategy_pct / 100.0), 4)

    def max_asset_class_notional(self, equity):
        return quantize(equity * (self.max_asset_class_pct / 100.0), 4)
