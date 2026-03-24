import json
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class CycleMemory:

    def __init__(self, base_path="memory"):

        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

        self.cycle_log = []
        self.lineage_graph = defaultdict(int)
        self.regime_history = defaultdict(list)
        self.alpha_decay = defaultdict(float)
        self.mutation_success = defaultdict(float)

        self._load_all()

    # ==========================================================
    # LOAD / SAVE
    # ==========================================================

    def _path(self, name):
        return os.path.join(self.base_path, name)

    def _load_json(self, name, default):

        p = self._path(name)

        if not os.path.exists(p):
            return default

        try:
            with open(p, "r") as f:
                return json.load(f)
        except Exception:
            logger.warning(f"[cycle_memory] failed loading {name}")
            return default

    def _save_json(self, name, data):

        tmp = self._path(name + ".tmp")

        with open(tmp, "w") as f:
            json.dump(data, f)

        os.replace(tmp, self._path(name))

    def _load_all(self):

        self.cycle_log = self._load_json("cycle_log.json", [])
        self.lineage_graph = defaultdict(
            int,
            self._load_json("lineage_graph.json", {}),
        )
        self.regime_history = defaultdict(
            list,
            self._load_json("regime_history.json", {}),
        )
        self.alpha_decay = defaultdict(
            float,
            self._load_json("alpha_decay.json", {}),
        )
        self.mutation_success = defaultdict(
            float,
            self._load_json("mutation_success.json", {}),
        )

        logger.info("[cycle_memory] persistent memory loaded")

    def flush(self):

        self._save_json("cycle_log.json", self.cycle_log)
        self._save_json("lineage_graph.json", dict(self.lineage_graph))
        self._save_json("regime_history.json", dict(self.regime_history))
        self._save_json("alpha_decay.json", dict(self.alpha_decay))
        self._save_json("mutation_success.json", dict(self.mutation_success))

    # ==========================================================
    # CYCLE RECORD
    # ==========================================================

    def record_cycle(
        self,
        cycle_id,
        promoted,
        evaluated,
        resolution,
    ):

        self.cycle_log.append(
            {
                "cycle": cycle_id,
                "promoted": len(promoted),
                "evaluated": evaluated,
                "resolution": resolution,
            }
        )

        for g in promoted:
            key = f"{g.family}_{g.symbol}"
            self.lineage_graph[key] += 1

        self.flush()

    # ==========================================================
    # REGIME TRACKING
    # ==========================================================

    def record_regime(self, symbol, resolution, regime):

        key = f"{symbol}_{resolution}"

        self.regime_history[key].append(regime)

    # ==========================================================
    # DECAY PRESSURE
    # ==========================================================

    def alpha_decay_pressure(self, genome):

        key = f"{genome.family}_{genome.symbol}"

        pressure = self.alpha_decay[key]

        self.alpha_decay[key] += 0.03

        return pressure

    # ==========================================================
    # MUTATION PRESSURE
    # ==========================================================

    def lineage_pressure(self):

        if not self.lineage_graph:
            return 0.5

        avg = sum(self.lineage_graph.values()) / len(self.lineage_graph)

        return min(1.0, avg / 10)

    # ==========================================================
    # PROMOTION OUTCOME FEEDBACK
    # ==========================================================

    def record_mutation_success(self, genome, success):

        key = genome.family

        if success:
            self.mutation_success[key] += 0.1
        else:
            self.mutation_success[key] -= 0.05