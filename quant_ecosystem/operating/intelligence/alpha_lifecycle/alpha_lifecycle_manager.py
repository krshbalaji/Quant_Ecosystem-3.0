import logging

logger = logging.getLogger(__name__)


class AlphaLifecycleManager:

    def __init__(
        self,
        alpha_state,
        probation_engine,
        maturity_scaler,
        retirement_engine,
        resurrection_engine,
        portfolio_engine,
        regime_memory,
    ):
        self.state = alpha_state
        self.probation = probation_engine
        self.scaler = maturity_scaler
        self.retirement = retirement_engine
        self.resurrection = resurrection_engine
        self.portfolio = portfolio_engine
        self.regime_memory = regime_memory

    # ==========================================
    # UPDATE LOOP
    # ==========================================

    def update(self):

        for g in list(self.portfolio.book.live_alphas):

            self.state.increment_age(g)

            current_state = self.state.get(g)

            if current_state == "NEW":
                self.state.set(g, "PROBATION")

            elif current_state == "PROBATION":

                if self.probation.allow_scale(g, self.state):
                    self.state.set(g, "MATURE")

            elif current_state == "MATURE":

                factor = self.scaler.scale_factor(g, self.state)
                self.portfolio.book.allocations[g] *= factor

                if self.retirement.should_retire(g, self.state):
                    self.state.set(g, "DECAYING")

            elif current_state == "DECAYING":

                self.portfolio.book.remove(g)
                self.state.set(g, "RETIRED")

        # Resurrection Scan
        for g, st in self.state.state.items():

            if st == "RETIRED":

                if self.resurrection.should_resurrect(
                    g,
                    self.regime_memory,
                ):
                    self.portfolio.book.add(g, 0.1)
                    self.state.set(g, "RESURRECTED")

                    logger.info(
                        f"[lifecycle] resurrected alpha {g.symbol}"
                    )