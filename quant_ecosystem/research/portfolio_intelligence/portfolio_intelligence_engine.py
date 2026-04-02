import logging

logger = logging.getLogger(__name__)


class PortfolioIntelligenceEngine:

    def __init__(
        self,
        alpha_book,
        correlation_engine,
        exposure_controller,
        allocator,
    ):
        self.book = alpha_book
        self.corr = correlation_engine
        self.exposure = exposure_controller
        self.allocator = allocator

    # ==========================================
    # INGEST NEW ALPHAS
    # ==========================================

    def consider(self, genomes):

        for g in genomes:

            alloc = self.allocator.allocation_size(g)

            if alloc <= 0:
                continue

            if not self._correlation_ok(g):
                continue

            if not self.exposure.allow(g, alloc):
                continue

            self.book.add(g, alloc)

            logger.info(
                f"[portfolio] accepted alpha {g.family} {g.symbol}"
            )

    # ==========================================
    # CORRELATION CHECK
    # ==========================================

    def _correlation_ok(self, genome):

        for live in self.book.live_alphas:

            if abs(self.corr.estimate(genome, live)) > 0.7:
                return False

        return True

    # ==========================================
    # DECAY DETECTION
    # ==========================================

    def decay_scan(self):

        for g in list(self.book.live_alphas):

            pnl = self.book.pnl[g]

            if pnl < -2:
                self.book.remove(g)

                logger.info(
                    f"[portfolio] decay removal {g.symbol}"
                )