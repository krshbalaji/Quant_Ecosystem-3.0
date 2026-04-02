from typing import Dict, List, Tuple


class LifecycleParliamentEngine:
    """
    Institutional lifecycle sovereignty engine.

    Multiple intelligence modules can propose lifecycle stages.
    Parliament computes weighted consensus → final stage.
    """

    def __init__(self):

        self.vote_weights = {
            "strategy_bank": 5.0,
            "meta_brain": 4.0,
            "survival_engine": 3.0,
            "evolution_engine": 2.0,
            "autonomous_controller": 2.0,
        }

    def decide_stage(
        self,
        strategy_id: str,
        proposals: List[Tuple[str, str]],
    ) -> str:

        """
        proposals = [
            ("meta_brain", "LIVE"),
            ("strategy_bank", "SHADOW"),
            ("survival_engine", "REDUCED")
        ]
        """

        score: Dict[str, float] = {}

        for source, stage in proposals:
            weight = self.vote_weights.get(source, 1.0)
            stage = str(stage).upper()

            score[stage] = score.get(stage, 0.0) + weight

        if not score:
            return "RESEARCH"

        final_stage = sorted(
            score.items(),
            key=lambda x: x[1],
            reverse=True
        )[0][0]

        return final_stage