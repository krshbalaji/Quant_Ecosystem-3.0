import logging
import time

from quant_ecosystem.platform_runtime.alpha_spine_integrator import AlphaSpineIntegrator
from quant_ecosystem.autonomous_research.autonomous_research_loop import AutonomousResearchLoop
from quant_ecosystem.portfolio.portfolio_engine import PortfolioEngine
from quant_ecosystem.research.alpha_intelligence.strategy_discovery_engine import StrategyDiscoveryEngine
from quant_ecosystem.research.alpha_intelligence.promotion_probability_engine import PromotionProbabilityEngine
from quant_ecosystem.research.alpha_intelligence.cycle_memory import CycleMemory


# ---------------- MOCK SUPPORT ----------------

class DummyLifecycle:
    def update(self):
        print("[MOCK] lifecycle update")

class DummyRotation:
    def evaluate_rotation(self,*args,**kwargs):
        print("[MOCK] rotation check")

class DummyPaperBridge:
    def route_signals(self, snapshot):
        print("[MOCK] routing signals")

class DummyRegimeMemory:

    def get_current_regime(self, *args, **kwargs):
        return "TREND_STRONG"

    def regime_stability(self, *args, **kwargs):
        return 0.7

    def regime_transition_risk(self, *args, **kwargs):
        return 0.3

class DummyEvolution:
    def lineage_score(self, g):
        return 0.5
    def ingest_promotions(self, p):
        pass

class DummyGrid:
    def evaluate_batch(self, genomes):
        for g in genomes:
            g.fitness_score = 0.7
            g.sharpe = 1.2
            g.max_dd = 0.1
        return genomes


# ---------------- INTELLIGENCE OBJECTS ----------------

discovery = StrategyDiscoveryEngine()

promotion = PromotionProbabilityEngine(
    regime_memory=DummyRegimeMemory(),
    cycle_memory=CycleMemory(),
)

research_loop = AutonomousResearchLoop(
    research_grid=DummyGrid(),
    discovery_engine=discovery,
    regime_memory=DummyRegimeMemory(),
    promotion_engine=promotion,
    alpha_evolution_engine=DummyEvolution(),
    cycle_memory=CycleMemory(),
    resolution="M15",
    symbol_universe=["NIFTY","BANKNIFTY"],
)


# ---------------- PORTFOLIO ----------------

alpha_book = type("AB", (), {"live_alphas": []})()

portfolio_engine = PortfolioEngine()
portfolio_engine.live_alphas = alpha_book.live_alphas

# -------- EXECUTION ----------
from quant_ecosystem.execution.paper_execution_bridge import PaperExecutionBridge

paper_bridge = PaperExecutionBridge(
    portfolio_engine=portfolio_engine,
    alpha_book=alpha_book
)

from quant_ecosystem.intelligence.simple_lifecycle_adapter import SimpleLifecycleAdapter
lifecycle_manager = SimpleLifecycleAdapter(
    alpha_book=alpha_book,
    execution_bridge=paper_bridge
)

# ---------------- SPINE ----------------

alpha_spine = AlphaSpineIntegrator(
    research_loop=research_loop,
    portfolio_engine=portfolio_engine,
    lifecycle_manager=lifecycle_manager,
    regime_rotation_engine=DummyRotation(),
    paper_bridge=paper_bridge,
    regime_memory=DummyRegimeMemory(),
    alpha_book=alpha_book,
    symbol_universe=["NIFTY","BANKNIFTY"],
    resolution="M15",
)


# ---------------- BOOT ----------------

logging.basicConfig(level=logging.INFO)

for i in range(5):
    print(f"\n===== BOOT CYCLE {i} =====")
    alpha_spine.on_bar({})
    time.sleep(1)