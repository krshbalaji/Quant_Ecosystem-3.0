"""Alpha Factory controller."""

from __future__ import annotations

from typing import Dict, List, Optional

from quant_ecosystem.alpha_factory.candidate_filter import CandidateFilter
from quant_ecosystem.alpha_factory.genome_pipeline import GenomePipeline
from quant_ecosystem.alpha_factory.idea_generator import IdeaGenerator
from quant_ecosystem.alpha_factory.promotion_pipeline import PromotionPipeline
from quant_ecosystem.alpha_factory.research_scheduler import ResearchScheduler


class AlphaFactoryController:
    """Automates strategy research pipeline at scale."""

    def __init__(
        self,
        genome_library,
        genome_generator,
        genome_evaluator,
        idea_generator: Optional[IdeaGenerator] = None,
        genome_pipeline: Optional[GenomePipeline] = None,
        candidate_filter: Optional[CandidateFilter] = None,
        promotion_pipeline: Optional[PromotionPipeline] = None,
        research_scheduler: Optional[ResearchScheduler] = None,
        strategy_bank_layer=None,
        shadow_trading_engine=None,
        random_count: int = 8,
        mutation_variants: int = 2,
        cross_children: int = 4,
        max_promotions: int = 3,
    ):
        self.genome_library = genome_library
        self.genome_generator = genome_generator
        self.genome_evaluator = genome_evaluator
        self.idea_generator = idea_generator or IdeaGenerator()
        self.genome_pipeline = genome_pipeline or GenomePipeline()
        self.candidate_filter = candidate_filter or CandidateFilter()
        self.promotion_pipeline = promotion_pipeline or PromotionPipeline()
        self.research_scheduler = research_scheduler or ResearchScheduler()
        self.strategy_bank_layer = strategy_bank_layer
        self.shadow_trading_engine = shadow_trading_engine
        self.random_count = int(random_count)
        self.mutation_variants = int(mutation_variants)
        self.cross_children = int(cross_children)
        self.max_promotions = int(max_promotions)
        self.last_report: Dict = {}
        self.last_events: List[Dict] = []

    def run_cycle(self) -> Dict:
        flags = self.research_scheduler.due()
        generated = []
        if flags.get("generate"):
            parents = self.genome_library.list(limit=50)
            generated = self.idea_generator.generate(
                genome_generator=self.genome_generator,
                parent_genomes=parents,
                random_count=self.random_count,
                mutation_variants=self.mutation_variants,
                cross_children=self.cross_children,
            )
            for genome in generated:
                if genome.get("genome_id"):
                    self.genome_library.upsert_dict(genome)

        reports = []
        filtered = []
        promoted = []
        shadow_candidates = []
        if flags.get("evaluate"):
            rows = self.genome_library.list(limit=300)
            _ = self.genome_pipeline.convert(rows)  # maintains stage mapping for pipeline visibility
            reports = self.genome_evaluator.evaluate_genomes(rows)
            for rep in reports:
                rep["trade_count"] = int(rep.get("components", {}).get("shadow", {}).get("trades", 0) or 0)
            filtered = self.candidate_filter.apply(reports)
            promoted = self.promotion_pipeline.promote(
                filtered_reports=filtered,
                strategy_bank_layer=self.strategy_bank_layer,
                shadow_trading_engine=self.shadow_trading_engine,
                max_promotions=self.max_promotions,
            )
            shadow_candidates = [item for item in filtered if item.get("trade_count", 0) >= 1]

        self.last_events = [
            {"type": "ALPHA_FACTORY_GENERATED", "count": len(generated)},
            {"type": "ALPHA_FACTORY_FILTERED", "count": len(filtered)},
            {"type": "ALPHA_FACTORY_PROMOTED", "count": len(promoted)},
        ]
        self.last_report = {
            "genomes_generated": len(generated),
            "candidates_filtered": len(filtered),
            "shadow_strategies": len(shadow_candidates),
            "promoted_strategies": promoted,
        }
        return dict(self.last_report)

