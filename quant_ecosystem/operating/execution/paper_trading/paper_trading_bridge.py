import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PaperTradingBridge:

    def __init__(
        self,
        capital_governor,
        execution_router,
        regime_memory,
        cycle_memory,
    ):
        self.capital_governor = capital_governor
        self.execution_router = execution_router
        self.regime_memory = regime_memory
        self.cycle_memory = cycle_memory

        self.live_alphas = []
        self.alpha_allocations = defaultdict(float)
        self.alpha_pnl = defaultdict(float)

    # ==========================================================
    # PORTFOLIO BUILD
    # ==========================================================

    def ingest_promoted(self, promoted):

        logger.info(f"[paper_bridge] ingesting {len(promoted)} promoted alphas")

        for g in promoted:

            allocation = self.capital_governor.allocate_alpha(g)

            if allocation <= 0:
                continue

            self.live_alphas.append(g)
            self.alpha_allocations[g] = allocation

    # ==========================================================
    # SIGNAL ROUTING
    # ==========================================================

    def route_signals(self, market_snapshot):

        for g in self.live_alphas:

            regime = self.regime_memory.get_current_regime(
                g.symbol,
                g.resolution,
            )

            if self._regime_shock(g, regime):
                self._deallocate(g)
                continue

            signal = getattr(g, "generate_signal", None)

            if not signal:
                continue

            order = signal(market_snapshot)

            if order:
                self.execution_router.route(order)

    # ==========================================================
    # REGIME SHOCK HANDLER
    # ==========================================================

    def _regime_shock(self, genome, current_regime):

        if getattr(genome, "trained_regime", None) != current_regime:
            return True

        return False

    # ==========================================================
    # DEALLOCATION
    # ==========================================================

    def _deallocate(self, genome):

        logger.info(
            f"[paper_bridge] regime shock → deallocating {genome.symbol}"
        )

        if genome in self.live_alphas:
            self.live_alphas.remove(genome)

    # ==========================================================
    # PNL FEEDBACK
    # ==========================================================

    def update_pnl(self, fills):

        for fill in fills:

            genome = fill.genome

            pnl = fill.pnl

            self.alpha_pnl[genome] += pnl

            success = pnl > 0

            self.cycle_memory.record_mutation_success(
                genome,
                success,
            )