"""Institutional strategy mutation engine.

This module mutates strategies in controlled layers, backtests variants, and
promotes only validated candidates into Strategy Bank storage.
It never executes orders or deploys directly to live trading.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.core.config_loader import Config
from quant_ecosystem.research.backtest.backtest_engine import BacktestEngine
from quant_ecosystem.strategy_bank.mutation.crossover_engine import CrossoverEngine
from quant_ecosystem.strategy_bank.mutation.parameter_mutator import ParameterMutator
from quant_ecosystem.strategy_bank.mutation.strategy_dna import StrategyDNA


class MutationEngine:
    """Generates and filters strategy mutations with strict fitness gates."""

    def __init__(
        self,
        config: Optional[Config] = None,
        backtest: Optional[BacktestEngine] = None,
        mutator: Optional[ParameterMutator] = None,
        crossover: Optional[CrossoverEngine] = None, **kwargs
    ):
        self.config = config or Config()
        self.enabled = bool(getattr(self.config, "enable_strategy_mutation", False))
        self.backtest = backtest or BacktestEngine()
        self.mutator = mutator or ParameterMutator()
        self.crossover = crossover or CrossoverEngine()
        self.max_daily = int(max(0, getattr(self.config, "mutation_rate_per_day", 2)))
        self.batch_size = int(max(1, getattr(self.config, "mutation_batch_size", 8)))
        self.min_sharpe = float(getattr(self.config, "mutation_min_sharpe", 1.2))
        self.min_profit_factor = float(getattr(self.config, "mutation_min_profit_factor", 1.3))
        self.max_drawdown = float(getattr(self.config, "mutation_max_drawdown", 15.0))
        self.max_capital_exposure_pct = float(
            getattr(self.config, "mutation_max_capital_exposure_pct", 30.0)
        )
        self.state_file = Path("strategy_bank/metadata/mutation_state.json")
        self.candidate_dir = Path("strategy_bank/candidate")
        self.validated_dir = Path("strategy_bank/metadata/validated_variants")
        self.analytics_dir = Path("strategy_bank/analytics/mutation_runs")
        self.candidate_dir.mkdir(parents=True, exist_ok=True)
        self.validated_dir.mkdir(parents=True, exist_ok=True)
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

    def run_daily(self, strategy_rows: Iterable[Dict]) -> List[Dict]:
        if not self.enabled or self.max_daily <= 0:
            return []

        state = self._read_state()
        today = datetime.utcnow().strftime("%Y%m%d")
        if state.get("date") != today:
            state = {"date": today, "count": 0}

        produced: List[Dict] = []
        rows = [row for row in strategy_rows if row.get("stage") in {"PAPER", "PAPER_SHADOW", "LIVE"}]
        if not rows:
            return produced

        runs = []
        while state["count"] < self.max_daily:
            evaluated = self._generate_batch(rows, self.batch_size)
            if not evaluated:
                state["count"] += 1
                continue
            best = max(evaluated, key=lambda item: item["score"])
            runs.append(
                {
                    "run_index": state["count"] + 1,
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "generated": len(evaluated),
                    "best_score": round(float(best["score"]), 4),
                    "best_metrics": best["metrics"],
                    "best_layers": best["layers"],
                    "accepted": bool(best.get("accepted", False)),
                }
            )
            if best.get("accepted", False):
                file_path = self._write_candidate(best["dna"], best["metrics"], best["score"], best["layers"])
                produced.append(
                    {
                        "path": str(file_path),
                        "metrics": best["metrics"],
                        "dna": best["dna"].to_dict(),
                        "score": round(float(best["score"]), 4),
                        "layers": list(best["layers"]),
                    }
                )
            state["count"] += 1

        self._write_analytics(runs)
        self._write_state(state)
        return produced

    def _generate_batch(self, rows: List[Dict], batch_size: int) -> List[Dict]:
        out = []
        for _ in range(max(1, batch_size)):
            child, layers = self._generate_child(rows)
            metrics = self._evaluate(child)
            score = self._score(metrics)
            accepted = self._passes_gate(metrics, child)
            out.append(
                {
                    "dna": child,
                    "layers": layers,
                    "metrics": metrics,
                    "score": score,
                    "accepted": accepted,
                }
            )
        return out

    def _generate_child(self, rows: List[Dict]) -> tuple[StrategyDNA, List[str]]:
        layers = []
        if len(rows) >= 2 and random.random() < 0.5:
            left, right = random.sample(rows, 2)
            dna = self.crossover.crossover(self._row_to_dna(left), self._row_to_dna(right))
            layers.append("crossover")
        else:
            dna = self._row_to_dna(random.choice(rows))

        dna = self.mutator.mutate(dna)
        layers.append("parameter_mutation")
        if random.random() < 0.5:
            dna = self.mutator.swap_indicator(dna)
            layers.append("indicator_mutation")
        if random.random() < 0.5:
            dna = self.mutator.tweak_logic(dna)
            layers.append("logic_mutation")
        if random.random() < 0.5:
            dna = self.mutator.mutate_timeframe(dna)
            layers.append("timeframe_mutation")
        if random.random() < 0.6:
            dna = self.mutator.mutate_risk_model(dna)
            layers.append("risk_model_mutation")
        return dna, layers

    def _row_to_dna(self, row: Dict) -> StrategyDNA:
        return StrategyDNA(
            entry_logic=str(row.get("entry_logic", "trend_follow_entry")),
            exit_logic=str(row.get("exit_logic", "fixed_exit")),
            stop_loss=float(row.get("stop_loss", 1.0)),
            take_profit=float(row.get("take_profit", 2.0)),
            indicators=list(row.get("indicators", ["ema", "rsi"])),
            parameters=dict(row.get("parameters", {"lookback": 20.0, "risk_multiple": 1.5})),
            timeframe=str(row.get("timeframe", "5m")),
            asset_class=str(row.get("asset_class", "stocks")),
        )

    def _evaluate(self, dna: StrategyDNA) -> Dict:
        # Backtest callable is generated from DNA logic.
        def synthetic_strategy(window: Dict) -> str:
            closes = window.get("close", [])
            if len(closes) < 5:
                return "HOLD"
            fast = int(max(3, dna.parameters.get("ema_fast", 8.0)))
            slow = int(max(fast + 1, dna.parameters.get("ema_slow", 21.0)))
            if len(closes) < slow + 2:
                return "HOLD"
            fast_avg = sum(closes[-fast:]) / fast
            slow_avg = sum(closes[-slow:]) / slow
            if fast_avg > slow_avg:
                return "BUY"
            if fast_avg < slow_avg:
                return "SELL"
            return "HOLD"

        return self.backtest.run(synthetic_strategy)

    def _passes_gate(self, metrics: Dict, dna: StrategyDNA) -> bool:
        if not self._passes_safety_limits(dna):
            return False
        return (
            float(metrics.get("sharpe", 0.0)) > self.min_sharpe
            and float(metrics.get("profit_factor", 0.0)) > self.min_profit_factor
            and float(metrics.get("max_dd", metrics.get("max_drawdown", 100.0))) < self.max_drawdown
        )

    def _passes_safety_limits(self, dna: StrategyDNA) -> bool:
        est_exposure = (
            float(dna.parameters.get("risk_multiple", 1.5))
            * max(0.1, float(dna.stop_loss))
            * 5.0
        )
        return est_exposure <= self.max_capital_exposure_pct

    def _score(self, metrics: Dict) -> float:
        sharpe = float(metrics.get("sharpe", 0.0))
        profit_factor = float(metrics.get("profit_factor", 0.0))
        expectancy = float(metrics.get("expectancy", 0.0))
        win_rate = float(metrics.get("win_rate", 0.0))
        drawdown = float(metrics.get("max_dd", metrics.get("max_drawdown", 0.0)))
        return (
            0.25 * sharpe
            + 0.25 * profit_factor
            + 0.20 * expectancy
            + 0.15 * win_rate
            - 0.15 * drawdown
        )

    def _write_candidate(self, dna: StrategyDNA, metrics: Dict, score: float, layers: List[str]) -> Path:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        strategy_id = f"mutant_{ts}"
        file_path = self.candidate_dir / f"{strategy_id}.json"
        payload = {
            "id": strategy_id,
            "stage": "CANDIDATE",
            "mutation_layers": list(layers),
            "score": round(float(score), 4),
            "dna": dna.to_dict(),
            "metrics": metrics,
            "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (self.validated_dir / f"{strategy_id}.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        return file_path

    def _read_state(self) -> Dict:
        if not self.state_file.exists():
            return {"date": "", "count": 0}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {"date": "", "count": 0}

    def _write_state(self, payload: Dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_analytics(self, runs: List[Dict]) -> None:
        if not runs:
            return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.analytics_dir / f"mutation_run_{ts}.json"
        path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
