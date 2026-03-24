import logging

logger = logging.getLogger(__name__)


class AlphaSpineIntegrator:

    def __init__(
        self,
        research_loop,
        portfolio_engine,
        lifecycle_manager,
        regime_rotation_engine,
        paper_bridge,
        regime_memory,
        alpha_book,
        symbol_universe,
        resolution,
    ):
        self.research_loop = research_loop
        self.portfolio_engine = portfolio_engine
        self.lifecycle = lifecycle_manager
        self.rotation = regime_rotation_engine
        self.paper_bridge = paper_bridge
        self.regime_memory = regime_memory
        self.alpha_book = alpha_book
        self.symbol_universe = symbol_universe
        self.resolution = resolution

        self.cycle_id = 0
                
    # ==========================================================
    # MAIN HEARTBEAT
    # ==========================================================

    def on_bar(self, market_snapshot):

        logger.info(f"[alpha_spine] heartbeat cycle={self.cycle_id}")

        promoted = self.research_loop.run_cycle(self.cycle_id)

        logger.info(f"[BOOT] promoted={len(promoted)}")

        for g in promoted:
            logger.info(f"[ALPHA_BIRTH] {g.family} {g.symbol}")

        self.portfolio_engine.consider(promoted)

        logger.info(
            f"[BOOT] portfolio_size={len(self.alpha_book.live_alphas)}"
        )

        self.lifecycle.update()

        self.rotation.evaluate_rotation(
            self.symbol_universe,
            self.resolution,
            self.regime_memory,
            self.alpha_book,
    )

        self.paper_bridge.route_signals(market_snapshot)

        self.cycle_id += 1

        # ------------------------------------------
        # 1️⃣ RESEARCH CYCLE
        # ------------------------------------------
        promoted = self.research_loop.run_cycle(self.cycle_id)

        # ------------------------------------------
        # 2️⃣ PORTFOLIO INTAKE
        # ------------------------------------------
        self.portfolio_engine.consider(promoted)

        # ------------------------------------------
        # 3️⃣ LIFECYCLE UPDATE
        # ------------------------------------------
        self.lifecycle.update()

        # ------------------------------------------
        # 4️⃣ REGIME ROTATION
        # ------------------------------------------
        self.rotation.evaluate_rotation(
            self.symbol_universe,
            self.resolution,
            self.regime_memory,
            self.alpha_book,
        )

        # ------------------------------------------
        # 5️⃣ EXECUTION ROUTING
        # ------------------------------------------
        self.paper_bridge.route_signals(market_snapshot)

        self.cycle_id += 1

    # ==========================================================
    # PNL FEEDBACK ENTRY
    # ==========================================================

    def on_fills(self, fills):

        self.paper_bridge.update_pnl(fills)