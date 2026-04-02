import json
from datetime import datetime
from pathlib import Path


class RuntimeStore:

    def __init__(self, output_dir="reporting/output/runtime", **kwargs):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_cycle(self, cycle_id, result, state):
        payload = {
            "timestamp": datetime.now().isoformat(),
            "cycle": cycle_id,
            "result": result,
            "state": {
                "equity": round(state.equity, 4),
                "cash_balance": round(state.cash_balance, 4),
                "realized_pnl": round(state.realized_pnl, 4),
                "unrealized_pnl": round(state.unrealized_pnl, 4),
                "fees_paid": round(state.fees_paid, 4),
                "drawdown_pct": round(state.total_drawdown_pct, 4),
                "consecutive_losses": state.consecutive_losses,
                "cooldown": state.cooldown,
                "open_positions": state.open_positions,
                "account_source": state.account_source,
                "last_reconciled_at": state.last_reconciled_at,
                "broker_positions_count": state.broker_positions_count,
                "broker_orders_count": state.broker_orders_count,
                "broker_trades_count": state.broker_trades_count,
            },
        }
        target = self.output_dir / f"cycle_{cycle_id:04d}.json"
        with target.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return str(target)
