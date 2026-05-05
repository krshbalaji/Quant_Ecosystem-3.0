from firestore_client import get_trade_history


def compute_metrics():
    trades = get_trade_history()

    if not trades:
        return {}

    total = len(trades)
    wins = sum(1 for t in trades if t["pnl"] > 0)
    total_pnl = sum(t["pnl"] for t in trades)

    return {
        "total_trades": total,
        "win_rate": round((wins / total) * 100, 2),
        "total_pnl": round(total_pnl, 2)
    }