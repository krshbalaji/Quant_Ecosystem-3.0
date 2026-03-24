import random
import time


class StrategyDiscoveryEngine:

    def __init__(self):

        self.templates_trend = [
            "momentum",
            "ma_cross",
            "breakout"
        ]

        self.templates_mean = [
            "mean_reversion",
            "rsi"
        ]

        self.templates_volatility = [
            "volatility_breakout",
            "breakout"
        ]

        self.performance_memory = []

    # -----------------------------------------------------

    def discover(self, batch_size=30):

        regime = self._detect_regime()

        genomes = []

        for _ in range(batch_size):

            template = self._select_template(regime)

            genome = self._build_genome(template, regime)

            genomes.append(genome)

        return genomes[:1]
        

    # -----------------------------------------------------

    def _detect_regime(self):

        r = random.random()

        if r < 0.33:
            return "trend"

        elif r < 0.66:
            return "mean"

        return "volatile"

    # -----------------------------------------------------

    def _select_template(self, regime):

        if self.performance_memory and random.random() < 0.40:

            best = sorted(
                self.performance_memory,
                key=lambda x: x["fitness"],
                reverse=True
            )[:5]

            if best:
                return random.choice(best)["template"]

        if regime == "trend":
            return random.choice(self.templates_trend)

        elif regime == "mean":
            return random.choice(self.templates_mean)

        return random.choice(self.templates_volatility)

    # -----------------------------------------------------

    def _build_genome(self, template, regime):

        gid = f"arl_{template}_{int(time.time()*1000)%100000}"

        lookback = random.randint(12, 80)

        if regime == "trend":
            threshold = random.uniform(0.002, 0.02)

        elif regime == "mean":
            threshold = random.uniform(0.6, 2.4)

        else:
            threshold = random.uniform(0.01, 0.05)

        return {

            "genome_id": gid,

            "signal_gene": {
                "indicator": template,
                "lookback": lookback,
                "threshold": threshold,
                "slow_period": random.randint(20, 180)
            },

            "risk_gene": {
                "position_size": random.uniform(0.5, 1.8),
                "stop_loss": random.uniform(0.8, 3.5),
                "take_profit": random.uniform(1.2, 6.0)
            },

            "meta": {
                "regime_target": regime,
                "created_ts": time.time()
            }
        }

    # -----------------------------------------------------

    def record_performance(self, genome, fitness):

        self.performance_memory.append({

            "template": genome["signal_gene"]["indicator"],
            "fitness": fitness
        })

        if len(self.performance_memory) > 800:
            self.performance_memory = self.performance_memory[-800:]