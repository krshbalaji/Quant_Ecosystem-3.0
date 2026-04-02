import logging

logger = logging.getLogger(__name__)


class RegimeRotationEngine:

    def __init__(
        self,
        shift_detector,
        regime_scorer,
        rotation_allocator,
        portfolio_engine,
        discovery_engine,
    ):
        self.shift_detector = shift_detector
        self.regime_scorer = regime_scorer
        self.rotation_allocator = rotation_allocator
        self.portfolio_engine = portfolio_engine
        self.discovery_engine = discovery_engine

    # ==================================================
    # GLOBAL ROTATION CHECK
    # ==================================================

    def evaluate_rotation(
        self,
        symbol_universe,
        resolution,
        regime_memory,
        alpha_book,
    ):

        regime_shift = False

        for symbol in symbol_universe:

            shifted, regime = self.shift_detector.detect(
                symbol,
                resolution,
                regime_memory,
            )

            if shifted:
                regime_shift = True

        mismatch = self.regime_scorer.score(
            alpha_book,
            regime_memory,
        )

        pressure = self.rotation_allocator.rotation_pressure(
            mismatch
        )

        if regime_shift or pressure > 0.5:

            logger.info(
                f"[rotation] regime shift detected | pressure={pressure}"
            )

            self._rotate_portfolio(alpha_book, pressure)

            self._accelerate_discovery(pressure)

    # ==================================================
    # PORTFOLIO ROTATION
    # ==================================================

    def _rotate_portfolio(self, alpha_book, pressure):

        removal_count = int(len(alpha_book.live_alphas) * pressure)

        for g in list(alpha_book.live_alphas)[:removal_count]:
            alpha_book.remove(g)

            logger.info(
                f"[rotation] removed alpha {g.symbol}"
            )

    # ==================================================
    # DISCOVERY ACCELERATION
    # ==================================================

    def _accelerate_discovery(self, pressure):

        self.discovery_engine.discovery_urgency = pressure