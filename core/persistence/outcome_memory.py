import json
from pathlib import Path

from utils.decimal_utils import quantize


class OutcomeMemory:

    def __init__(self, path="core/persistence/outcome_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load()

    def signal_bias(self, strategy_id, symbol, regime, trade_type):
        key = self._key(strategy_id=strategy_id, symbol=symbol, regime=regime, trade_type=trade_type)
        stats = self.memory.get(key)
        if not stats:
            return 0.0

        trades = max(int(stats.get("trades", 0)), 0)
        closed = max(int(stats.get("closed", 0)), 0)
        wins = max(int(stats.get("wins", 0)), 0)
        expectancy = float(stats.get("expectancy", 0.0))
        if trades < 10 or closed < 5:
            return 0.0

        win_rate = wins / max(closed, 1)
        raw = (win_rate - 0.5) * 0.2 + (expectancy * 0.02)
        return quantize(max(-0.12, min(raw, 0.12)), 6)

    def update_from_trades(self, trades):
        for trade in trades:
            key = self._key(
                strategy_id=trade.get("strategy_id"),
                symbol=trade.get("symbol"),
                regime=trade.get("regime"),
                trade_type=trade.get("trade_type"),
            )
            row = self.memory.get(
                key,
                {"trades": 0, "closed": 0, "wins": 0, "losses": 0, "sum_realized": 0.0, "sum_cycle": 0.0, "expectancy": 0.0},
            )

            row["trades"] += 1
            cycle = float(trade.get("cycle_pnl", 0.0))
            realized = float(trade.get("realized_pnl", 0.0))
            row["sum_cycle"] = quantize(float(row.get("sum_cycle", 0.0)) + cycle, 6)

            if bool(trade.get("closed_trade", False)) and abs(realized) > 0.0:
                row["closed"] += 1
                row["sum_realized"] = quantize(float(row.get("sum_realized", 0.0)) + realized, 6)
                if realized > 0:
                    row["wins"] += 1
                elif realized < 0:
                    row["losses"] += 1

            closed = max(int(row.get("closed", 0)), 0)
            if closed > 0:
                row["expectancy"] = quantize(float(row.get("sum_realized", 0.0)) / closed, 6)
            self.memory[key] = row

        self._save()

    def _key(self, strategy_id, symbol, regime, trade_type):
        s = str(strategy_id or "na").upper()
        y = str(symbol or "na").upper()
        r = str(regime or "na").upper()
        t = str(trade_type or "na").upper()
        return f"{s}|{y}|{r}|{t}"

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self):
        self.path.write_text(json.dumps(self.memory, indent=2), encoding="utf-8")
