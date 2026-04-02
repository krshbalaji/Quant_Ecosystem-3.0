"""
Self-learning module for strategy performance accumulation and capital management.
"""

from __future__ import annotations


class LearningEngine:
    def __init__(self):
        self.trade_history = []

    def record_trade(self, trade):
        if not isinstance(trade, dict):
            return
        self.trade_history.append(trade)

    def evaluate(self):
        if not self.trade_history:
            return {}

        wins = [t for t in self.trade_history if float(t.get("pnl", 0.0)) > 0]
        losses = [t for t in self.trade_history if float(t.get("pnl", 0.0)) <= 0]

        win_rate = len(wins) / len(self.trade_history)
        avg_win = sum(float(t.get("pnl", 0.0)) for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(float(t.get("pnl", 0.0)) for t in losses) / len(losses) if losses else 0.0

        return {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }
