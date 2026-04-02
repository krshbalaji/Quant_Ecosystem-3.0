class PortfolioCapitalGovernor:
    """
    Final portfolio capital authority.

    Decides whether a signal is allowed to execute
    based on portfolio state, regime and risk posture.
    """

    def __init__(
        self,
        max_total_exposure_pct: float = 100.0,
        max_strategy_exposure_pct: float = 30.0,
    ):
        self.max_total_exposure_pct = float(max_total_exposure_pct)
        self.max_strategy_exposure_pct = float(max_strategy_exposure_pct)

        self.current_total_exposure = 0.0
        self.strategy_exposure = {}

    # -----------------------------------------------------

    def update_portfolio_state(self, exposure_map: dict):
        self.strategy_exposure = dict(exposure_map)
        self.current_total_exposure = sum(exposure_map.values())

    # -----------------------------------------------------

    def allow_execution(self, signal: dict, regime: str):

        sid = str(signal.get("strategy_id"))

        proposed = float(signal.get("allocation_pct", 0.0))

        if proposed <= 0:
            return False, "zero_allocation"

        if proposed > self.max_strategy_exposure_pct:
            return False, "strategy_cap_breach"

        if self.current_total_exposure + proposed > self.max_total_exposure_pct:
            return False, "portfolio_cap_breach"

        return True, "approved"