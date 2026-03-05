import random


class BacktestEngine:

    def run(self, strategy_callable, periods=260):
        closes = self._generate_prices(periods=periods)
        pnls = []
        position = 0

        for index in range(30, len(closes)):
            window = {"close": closes[: index + 1]}
            decision = "HOLD"
            try:
                decision = strategy_callable(window)
            except Exception:
                decision = "HOLD"

            if decision == "BUY":
                position = 1
            elif decision == "SELL":
                position = -1

            prev = closes[index - 1]
            cur = closes[index]
            ret = 0.0 if prev == 0 else ((cur - prev) / prev)
            pnls.append(ret * position)

        return self._metrics(pnls)

    def _generate_prices(self, periods):
        series = []
        price = 100.0
        for _ in range(periods):
            price *= 1 + random.uniform(-0.015, 0.015)
            series.append(round(price, 4))
        return series

    def _metrics(self, returns):
        if not returns:
            return {
                "win_rate": 0.0,
                "expectancy": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "expectancy_rolling_100": 0.0,
                "max_dd": 0.0,
                "profit_factor": 0.0,
                "sharpe": 0.0,
                "returns": [],
            }

        wins = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]
        win_rate = (len(wins) / len(returns)) * 100.0
        loss_rate = 100.0 - win_rate

        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss_abs = (abs(sum(losses)) / len(losses)) if losses else 0.0

        expectancy = (win_rate / 100.0 * avg_win) - (loss_rate / 100.0 * avg_loss_abs)
        expectancy_rolling_100 = self._rolling_expectancy(returns, window=100)

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        sharpe = self._sharpe(returns)
        max_dd = self._max_drawdown(returns)

        return {
            "win_rate": round(win_rate, 4),
            "expectancy": round(expectancy * 100.0, 4),
            "avg_win": round(avg_win * 100.0, 4),
            "avg_loss": round(avg_loss_abs * 100.0, 4),
            "expectancy_rolling_100": round(expectancy_rolling_100 * 100.0, 4),
            "max_dd": round(max_dd, 4),
            "profit_factor": round(profit_factor, 4),
            "sharpe": round(sharpe, 4),
            "returns": [round(item, 6) for item in returns[-200:]],
        }

    def _rolling_expectancy(self, returns, window=100):
        sample = returns[-window:] if len(returns) >= window else returns
        if not sample:
            return 0.0

        wins = [value for value in sample if value > 0]
        losses = [value for value in sample if value < 0]
        win_rate = len(wins) / len(sample)
        loss_rate = 1.0 - win_rate
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss_abs = (abs(sum(losses)) / len(losses)) if losses else 0.0
        return (win_rate * avg_win) - (loss_rate * avg_loss_abs)

    def _sharpe(self, returns):
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((x - mean) ** 2 for x in returns) / len(returns)
        std = var ** 0.5
        if std == 0:
            return 0.0
        return (mean / std) * (252 ** 0.5)

    def _max_drawdown(self, returns):
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for ret in returns:
            equity *= 1 + ret
            peak = max(peak, equity)
            dd = ((peak - equity) / peak) * 100.0 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

import numpy as np


class AlphaBacktestEngine:

    def __init__(self, market_data_engine):
        self.market_data_engine = market_data_engine

    def backtest(self, strategy, symbol):

        data = self.market_data_engine.get_close_series(symbol)

        if len(data) < 100:
            return None

        pnl = []
        position = 0
        entry = None

        for i in range(50, len(data)):

            snapshot = {
                "close": data[:i]
            }

            signal = strategy.generate_signal(snapshot)

            price = data[i]

            if signal == "BUY" and position == 0:
                position = 1
                entry = price

            elif signal == "SELL" and position == 1:
                pnl.append(price - entry)
                position = 0

        if len(pnl) == 0:
            return None

        pnl = np.array(pnl)

        sharpe = pnl.mean() / (pnl.std() + 1e-6)

        return {
            "trades": len(pnl),
            "pnl": pnl.sum(),
            "sharpe": sharpe
        }