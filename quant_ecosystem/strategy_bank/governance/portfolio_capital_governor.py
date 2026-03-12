class PortfolioCapitalGovernor:
    """
    Final sovereign authority over capital deployment.

    Even if:
    - strategy is LIVE
    - execution token valid
    - signal strong

    Governor can block trade.
    """

    def __init__(self, state):
        self.state = state

    def allow_execution(self, signal, regime):

        # --- Portfolio soft drawdown throttle ---
        dd = float(getattr(self.state, "drawdown_pct", 0))

        if dd > 5:
            return False, "portfolio_soft_drawdown"

        # --- Hard crisis regime freeze ---
        if str(regime).upper() in {"CRISIS", "PANIC"}:
            return False, "regime_block"

        return True, "ok"