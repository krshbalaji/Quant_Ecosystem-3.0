"""
Evolution engine for autonomous strategy population management.
"""

import random
import logging
import uuid

logger = logging.getLogger(__name__)


class EvolutionEngine:

    def __init__(self):
        self.strategy_scores = {}
        self.population = []

    def register(self, strategy_id):
        if not strategy_id:
            return
        if strategy_id not in self.strategy_scores:
            self.strategy_scores[strategy_id] = []
        if strategy_id not in self.population:
            self.population.append(strategy_id)

    def record(self, strategy_id, pnl):
        if not strategy_id:
            return
        self.strategy_scores.setdefault(strategy_id, []).append(float(pnl or 0.0))
        if strategy_id not in self.population:
            self.population.append(strategy_id)

    def score(self, strategy_id):
        trades = self.strategy_scores.get(strategy_id, [])
        if not trades:
            return 0.0
        return sum(trades) / len(trades)

    def select_top(self, top_n=3):
        ranked = sorted(
            self.strategy_scores.items(),
            key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0,
            reverse=True,
        )
        top = [k for k, _ in ranked[:top_n]]
        return top

    def mutate(self, base_strategy):
        if not callable(base_strategy):
            return None

        factor_entry = random.uniform(0.8, 1.2)
        factor_exit = random.uniform(0.8, 1.2)

        def mutated_strategy(market_data):
            raw = base_strategy(market_data) or {}
            if not isinstance(raw, dict):
                return raw

            out = dict(raw)
            if "confidence" in out:
                out["confidence"] = min(1.0, max(0.0, float(out.get("confidence", 0.0)) * random.uniform(0.9, 1.1)))
            out["strategy_id"] = f"mutated_{out.get('strategy_id', 'unknown')}_{uuid.uuid4().hex[:6]}"

            # Add synthetic entry/exit thresholds to mutate behavior if unavailable
            out["entry_threshold"] = float(out.get("entry_threshold", 0.05)) * factor_entry
            out["exit_threshold"] = float(out.get("exit_threshold", 0.02)) * factor_exit
            return out

        return mutated_strategy

    def evolve_population(self, router):
        if not router or not getattr(router, "strategy_engine", None):
            return

        if not hasattr(router.strategy_engine, "registry"):
            return

        # score and select top strategies
        top_strategies = self.select_top(top_n=3)
        logger.info("[EVOLUTION] top_strategies=%s", top_strategies)

        # mutation + exploration
        for src in top_strategies[:2]:
            base = router.strategy_engine.registry.get(src)
            if callable(base):
                mutated = self.mutate(base)
                if mutated:
                    new_id = f"mutated_{src}_{uuid.uuid4().hex[:6]}"
                    try:
                        router.strategy_engine.registry.register(new_id, mutated)
                        self.register(new_id)
                        logger.info("[EVOLUTION] mutation registered = %s", new_id)
                    except Exception as e:
                        logger.warning("Evolution mutation failed for %s: %s", src, e)

        # prune worst performers
        scores = {sid: self.score(sid) for sid in self.population}
        worst = sorted(scores.items(), key=lambda x: x[1])[:2]
        for sid, score in worst:
            if score < 0 and hasattr(router.strategy_engine.registry, "unregister"):
                router.strategy_engine.registry.unregister(sid)
                if sid in self.population:
                    self.population.remove(sid)
                logger.info("[EVOLUTION] removed weak strategy %s score=%s", sid, score)

        # keep only top 3 in population
        sorted_by_score = sorted(self.population, key=lambda x: self.score(x), reverse=True)
        keep = sorted_by_score[:3]
        for sid in list(self.population):
            if sid not in keep:
                self.population.remove(sid)
        logger.info("[EVOLUTION] population size=%d keep=%s", len(self.population), keep)

        # optional random exploration
        if random.random() < 0.1:
            random_id = f"explore_{uuid.uuid4().hex[:6]}"
            def random_strategy(market_data):
                return {
                    "symbol": market_data.get("symbol") if isinstance(market_data, dict) else "",
                    "side": random.choice(["BUY", "SELL"]),
                    "confidence": random.uniform(0.1, 0.5),
                    "strategy_id": random_id,
                }
            router.strategy_engine.registry.register(random_id, random_strategy)
            self.register(random_id)
            logger.info("[EVOLUTION] exploration strategy added %s", random_id)
