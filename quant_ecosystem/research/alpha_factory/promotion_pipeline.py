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
        
        candidates = []

        for report in list(filtered_reports or [])[: max(1, int(max_promotions))]:

            genome_id = str(report.get("genome_id", report.get("strategy_id", ""))).strip()
            strategy_id = f"genome_{genome_id}" if genome_id else str(report.get("strategy_id", ""))

            candidate = {
                "id": strategy_id,
                "genome_id": genome_id,
                "stage": "DISCOVERED",
                "fitness_score": float(report.get("fitness_score", 0.0) or 0.0),
                "source": "alpha_factory"
            }

            candidates.append(candidate)

        return candidates

