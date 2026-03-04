"""Promotion stages for Alpha Factory strategies."""

from __future__ import annotations

from typing import Dict, Iterable, List


class PromotionPipeline:
    """Moves candidates through GENOME -> BACKTEST -> SHADOW -> PAPER -> LIVE."""

    STAGES = ("GENOME", "BACKTEST", "SHADOW", "PAPER", "LIVE")

    def promote(
        self,
        filtered_reports: Iterable[Dict],
        strategy_bank_layer=None,
        shadow_trading_engine=None,
        max_promotions: int = 5,
    ) -> List[Dict]:
        promoted = []
        for report in list(filtered_reports or [])[: max(1, int(max_promotions))]:
            genome_id = str(report.get("genome_id", report.get("strategy_id", ""))).strip()
            strategy_id = f"genome_{genome_id}" if genome_id else str(report.get("strategy_id", ""))
            event = {
                "strategy_id": strategy_id,
                "genome_id": genome_id,
                "promotion_stage": "PAPER",
                "fitness_score": float(report.get("fitness_score", 0.0) or 0.0),
            }
            promoted.append(event)

            # Register in shadow as a tracked strategy.
            if shadow_trading_engine is not None:
                try:
                    shadow_trading_engine.register_shadow_strategies([{"id": strategy_id}])
                except Exception:
                    pass

            # Light-touch strategy-bank registration/update.
            if strategy_bank_layer is not None and hasattr(strategy_bank_layer, "bank_engine"):
                bank = strategy_bank_layer.bank_engine
                if bank is not None and hasattr(bank, "registry"):
                    try:
                        if hasattr(bank.registry, "upsert"):
                            bank.registry.upsert(
                                {
                                    "id": strategy_id,
                                    "name": strategy_id,
                                    "stage": "PAPER_SHADOW",
                                    "active": False,
                                    "allocation_pct": 0.0,
                                    "score": float(report.get("fitness_score", 0.0) or 0.0),
                                    "category": "genome",
                                }
                            )
                    except Exception:
                        pass
        return promoted

