"""Backtest engine wrapper for Strategy Lab."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from research.backtest.backtest_engine import BacktestEngine as CoreBacktestEngine


class BacktestEngine:
    """Runs sandbox backtests for generated/mutated strategies."""

    def __init__(self, core_engine: Optional[CoreBacktestEngine] = None, microstructure_simulator=None):
        self.core_engine = core_engine or CoreBacktestEngine()
        self.microstructure_simulator = microstructure_simulator

    def run_strategy(self, strategy: Dict, periods: int = 260) -> Dict:
        """Run a single strategy backtest and return metrics."""
        callable_strategy = self._build_callable(strategy)
        metrics = self.core_engine.run(callable_strategy, periods=periods)
        if self.microstructure_simulator:
            params = dict(strategy.get("parameters", {}))
            metrics = self.microstructure_simulator.apply_to_backtest_metrics(
                metrics=metrics,
                asset_class=str(strategy.get("asset_class", "stocks")),
                average_order_size=float(params.get("avg_order_size", 10.0)),
                average_volatility=float(params.get("volatility", 0.2)),
                average_volume=float(params.get("volume", 150000.0)),
                average_depth=float(params.get("market_depth", 80000.0)),
            )
        metrics["volatility"] = self._volatility(metrics.get("returns", []))
        metrics["sample_size"] = len(metrics.get("returns", []))
        return metrics

    def run_batch(self, strategies: Iterable[Dict], periods: int = 260) -> List[Dict]:
        """Run a batch backtest and return enriched strategy rows."""
        out = []
        for strategy in strategies:
            item = dict(strategy)
            item["metrics"] = self.run_strategy(item, periods=periods)
            out.append(item)
        return out

    def _build_callable(self, strategy: Dict) -> Callable:
        params = dict(strategy.get("parameters", {}))
        ema_fast = int(max(3, float(params.get("ema_fast", 9))))
        ema_slow = int(max(ema_fast + 1, float(params.get("ema_slow", 21))))
        rsi_length = int(max(5, float(params.get("rsi_length", 14))))
        strategy_type = str(strategy.get("strategy_type", strategy.get("family", "momentum"))).lower()

        def callable_strategy(window: Dict) -> str:
            close = list(window.get("close", []))
            if len(close) < max(ema_slow + 2, rsi_length + 2):
                return "HOLD"

            fast = sum(close[-ema_fast:]) / ema_fast
            slow = sum(close[-ema_slow:]) / ema_slow
            mom = close[-1] - close[-rsi_length]
            # Simple RSI-like proxy for sandbox testing.
            gains = [max(0.0, close[i] - close[i - 1]) for i in range(len(close) - rsi_length, len(close))]
            losses = [max(0.0, close[i - 1] - close[i]) for i in range(len(close) - rsi_length, len(close))]
            avg_gain = sum(gains) / max(1, len(gains))
            avg_loss = sum(losses) / max(1, len(losses))
            rs = avg_gain / avg_loss if avg_loss > 1e-9 else 10.0
            rsi = 100.0 - (100.0 / (1.0 + rs))

            if strategy_type in {"trend_following", "momentum", "breakout"}:
                if fast > slow and mom > 0:
                    return "BUY"
                if fast < slow and mom < 0:
                    return "SELL"
            elif strategy_type in {"mean_reversion", "pairs_trading", "statistical_arbitrage"}:
                if rsi < 35:
                    return "BUY"
                if rsi > 65:
                    return "SELL"
            elif strategy_type == "volatility":
                if abs(mom / max(close[-rsi_length], 1e-9)) > 0.02:
                    return "BUY" if fast > slow else "SELL"
            return "HOLD"

        return callable_strategy

    def _volatility(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((x - mean) ** 2 for x in returns) / max(1, len(returns) - 1)
        return round(var ** 0.5, 6)
