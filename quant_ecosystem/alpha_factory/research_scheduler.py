"""Research workload scheduler for Alpha Factory."""

from __future__ import annotations

import time
from typing import Dict


class ResearchScheduler:
    """Controls generation/evaluation cadence."""

    def __init__(self, generate_every_sec: int = 1800, evaluate_every_sec: int = 900):
        self.generate_every_sec = max(30, int(generate_every_sec))
        self.evaluate_every_sec = max(30, int(evaluate_every_sec))
        self._last_generate_ts = 0.0
        self._last_evaluate_ts = 0.0

    def due(self) -> Dict:
        now = time.time()
        do_generate = (now - self._last_generate_ts) >= self.generate_every_sec
        do_evaluate = (now - self._last_evaluate_ts) >= self.evaluate_every_sec
        if do_generate:
            self._last_generate_ts = now
        if do_evaluate:
            self._last_evaluate_ts = now
        return {"generate": do_generate, "evaluate": do_evaluate, "now": now}

