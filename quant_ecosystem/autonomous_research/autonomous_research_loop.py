import logging
import random
from collections import defaultdict

logger = logging.getLogger(__name__)


class AutonomousResearchLoop:

    def __init__(
        self,
        research_grid,
        discovery_engine,
        regime_memory,
        promotion_engine,
        alpha_evolution_engine,
        cycle_memory,
        resolution,
        symbol_universe,
    ):
        self.grid = research_grid
        self.discovery_engine = discovery_engine
        self.regime_memory = regime_memory
        self.promotion_engine = promotion_engine
        self.alpha_evolution_engine = alpha_evolution_engine
        self.cycle_memory = cycle_memory
        self.resolution = resolution
        self.symbol_universe = symbol_universe

        self.symbol_alpha_density = defaultdict(float)

    # ==========================================================
    # MAIN LOOP
    # ==========================================================

    def run_cycle(self, cycle_id):

        logger.info(f"[research_loop] starting cycle {cycle_id} | {self.resolution}")

        weighted_symbols = self._compute_symbol_weights()

        genome_stream = []

        for symbol in weighted_symbols:

            regime = self.regime_memory.get_current_regime(symbol, self.resolution)

            discovered = self.discovery_engine.discover(
                symbol=symbol,
                resolution=self.resolution,
                regime=regime,
                alpha_density=self.symbol_alpha_density[symbol],
                cycle_memory=self.cycle_memory,
            )

            if not discovered:
                logger.warning(
                    "[research_loop] discovery_engine returned empty → fallback generator"
                )
                discovered = self._fallback_generator(symbol)

            scored = self._assign_confidence(discovered, regime)

            genome_stream.extend(scored)

        evaluated = self.grid.evaluate_batch(genome_stream)

        promoted = self.promotion_engine.select(evaluated)

        self._update_symbol_density(promoted)

        self.alpha_evolution_engine.ingest_promotions(promoted)

        self.cycle_memory.record_cycle(
            cycle_id=cycle_id,
            promoted=promoted,
            evaluated=len(evaluated),
            resolution=self.resolution,
        )

        logger.info(
            f"[research_loop] cycle {cycle_id} complete | promoted={len(promoted)}"
        )

        return promoted

    # ==========================================================
    # SYMBOL WEIGHTING
    # ==========================================================

    def _compute_symbol_weights(self):

        ranked = sorted(
            self.symbol_universe,
            key=lambda s: self.symbol_alpha_density[s]
        )

        exploration_zone = ranked[: int(len(ranked) * 0.4)]
        exploitation_zone = ranked[int(len(ranked) * 0.4):]

        ordered = exploration_zone + random.sample(exploitation_zone, len(exploitation_zone))

        return ordered

    # ==========================================================
    # CONFIDENCE SCORING
    # ==========================================================

    def _assign_confidence(self, genomes, regime):

        scored = []

        for g in genomes:

            lineage = self.alpha_evolution_engine.lineage_score(g)

            regime_alignment = self.discovery_engine.regime_alignment_score(
                g, regime
            )

            novelty = self.discovery_engine.structural_novelty_score(g)

            confidence = (
                0.4 * lineage
                + 0.4 * regime_alignment
                + 0.2 * novelty
            )

            g.alpha_confidence = confidence

            scored.append(g)

        return scored

    # ==========================================================
    # SYMBOL DENSITY UPDATE
    # ==========================================================

    def _update_symbol_density(self, promoted):

        for g in promoted:
            self.symbol_alpha_density[g.symbol] += 1.0

    # ==========================================================
    # FALLBACK GENERATOR
    # ==========================================================

    def _fallback_generator(self, symbol):

        return self.discovery_engine.random_genomes(symbol, self.resolution)