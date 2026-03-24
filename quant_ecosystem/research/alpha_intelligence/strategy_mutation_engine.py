import random
from typing import Dict, Any


class StrategyMutationEngine:
    """
    Regime aware mutation engine.
    """

    def __init__(self):
        print("🧬 StrategyMutationEngine initialized (Regime Aware)")

    def mutate(self, genome: Dict[str, Any], regime: str = "neutral"):

        params = genome.get("params", {})

        mutated = {}

        for k, v in params.items():

            if isinstance(v, int):
                shift = self._mutation_intensity(regime)
                mutated[k] = max(1, int(v + random.randint(-shift, shift)))

            elif isinstance(v, float):
                shift = self._mutation_intensity(regime) * 0.2
                mutated[k] = max(0.1, v + random.uniform(-shift, shift))

            else:
                mutated[k] = v

        genome["params"] = mutated
        genome["mutated"] = True

        return genome

    def _mutation_intensity(self, regime):

        if regime == "trend":
            return 10
        if regime == "range":
            return 5
        if regime == "volatile":
            return 15

        return 7