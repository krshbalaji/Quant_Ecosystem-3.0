from quant_ecosystem.autonomous_research import (
    opportunity_aging_engine,
    adaptive_weight_engine,
    alpha_evolution_memory,
    research_memory,
)


class AutonomousResearchLoopController:

    def evaluate_signal(
        self,
        signal_id,
        strategy_id,
        confidence,
        age_hours,
        base_weight=1.0,
        win_rate=50,
    ):
        aging = (
            opportunity_aging_engine
            .evaluate(
                confidence,
                age_hours,
            )
        )

        adjusted_weight = (
            adaptive_weight_engine
            .adjust_weight(
                base_weight,
                win_rate,
                aging["confidence"],
            )
        )

        prior = (
            research_memory.fetch(signal_id)
        )

        strategy = (
            alpha_evolution_memory.fetch(
                strategy_id
            )
        )

        return {
            "signal_id": signal_id,
            "strategy_id": strategy_id,
            "aging": aging,
            "adjusted_weight": adjusted_weight,
            "prior_signal": prior,
            "strategy_history": strategy,
            "retire": aging["retire"],
            "priority": (
                "HIGH"
                if adjusted_weight >= 1.2
                else "NORMAL"
            ),
        }


autonomous_research_loop_controller = (
    AutonomousResearchLoopController()
)