import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


ROOT_DIR = Path(__file__).resolve().parents[2]
POSITIONS_FILE = ROOT_DIR / "positions.json"
PAPER_LOG_FILE = ROOT_DIR / "paper_trades.jsonl"


@dataclass
class PortfolioSnapshot:
    positions: List[Dict[str, Any]] = field(default_factory=list)
    cash: float = 0.0
    equity: float = 0.0
    source: str = "NONE"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positions": list(self.positions),
            "cash": float(self.cash),
            "equity": float(self.equity),
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata or {}),
        }


def get_portfolio_snapshot(portfolio_engine: Optional[Any] = None) -> PortfolioSnapshot:
    """Return a best-effort read-only portfolio snapshot.

    Source precedence is intentionally conservative:
    1. Provided in-memory portfolio engine, if it has a snapshot.
    2. Local positions.json.
    3. Firestore portfolio collection, if credentials/imports are available.
    4. paper_trades.jsonl reconstructed positions.
    """
    attempts = []

    snapshot = read_portfolio_engine(portfolio_engine)
    attempts.append(snapshot.source)
    if snapshot.positions:
        snapshot.metadata["attempts"] = attempts
        return snapshot

    snapshot = read_positions_json()
    attempts.append(snapshot.source)
    if snapshot.positions:
        snapshot.metadata["attempts"] = attempts
        return snapshot

    snapshot = read_firestore_positions()
    attempts.append(snapshot.source)
    if snapshot.positions:
        snapshot.metadata["attempts"] = attempts
        return snapshot

    snapshot = read_paper_logs()
    attempts.append(snapshot.source)
    snapshot.metadata["attempts"] = attempts
    return snapshot


def read_positions_json(path: Path | str = POSITIONS_FILE) -> PortfolioSnapshot:
    path = Path(path)
    if not path.exists():
        return PortfolioSnapshot(source="positions.json", metadata={"available": False})

    try:
        raw = json.loads(path.read_text())
    except Exception as exc:
        return PortfolioSnapshot(source="positions.json", metadata={"error": str(exc)})

    positions = _positions_from_mapping(raw, source="positions.json")
    equity = _estimate_equity(positions)
    return PortfolioSnapshot(
        positions=positions,
        cash=0.0,
        equity=equity,
        source="positions.json",
        metadata={"available": True, "path": str(path)},
    )


def read_firestore_positions() -> PortfolioSnapshot:
    try:
        import firestore_client
    except Exception as exc:
        return PortfolioSnapshot(source="firestore", metadata={"available": False, "error": str(exc)})

    try:
        raw = firestore_client.get_positions() or {}
    except Exception as exc:
        return PortfolioSnapshot(source="firestore", metadata={"available": False, "error": str(exc)})

    positions = _positions_from_mapping(raw, source="firestore")
    equity = _estimate_equity(positions)
    return PortfolioSnapshot(
        positions=positions,
        cash=0.0,
        equity=equity,
        source="firestore",
        metadata={"available": True},
    )


def read_portfolio_engine(portfolio_engine: Optional[Any]) -> PortfolioSnapshot:
    if portfolio_engine is None:
        return PortfolioSnapshot(source="portfolio_engine", metadata={"available": False})

    try:
        if hasattr(portfolio_engine, "snapshot"):
            raw = portfolio_engine.snapshot()
        elif hasattr(portfolio_engine, "positions"):
            raw = getattr(portfolio_engine, "positions")
        else:
            return PortfolioSnapshot(source="portfolio_engine", metadata={"available": False})
    except Exception as exc:
        return PortfolioSnapshot(source="portfolio_engine", metadata={"error": str(exc)})

    positions = _positions_from_mapping(raw or {}, source="portfolio_engine")
    equity = _estimate_equity(positions)
    return PortfolioSnapshot(
        positions=positions,
        cash=0.0,
        equity=equity,
        source="portfolio_engine",
        metadata={"available": True},
    )


def read_paper_logs(path: Path | str = PAPER_LOG_FILE) -> PortfolioSnapshot:
    path = Path(path)
    if not path.exists():
        return PortfolioSnapshot(source="paper_trades.jsonl", metadata={"available": False})

    aggregate: Dict[str, Dict[str, Any]] = {}

    try:
        lines = path.read_text().splitlines()
    except Exception as exc:
        return PortfolioSnapshot(source="paper_trades.jsonl", metadata={"error": str(exc)})

    for line in lines:
        try:
            trade = json.loads(line)
        except json.JSONDecodeError:
            continue

        symbol = str(trade.get("symbol", "")).strip()
        if not symbol:
            continue

        qty = _safe_int(trade.get("qty", 0))
        price = _safe_float(trade.get("price", trade.get("entry_price", 0.0)))
        side = str(trade.get("side", "BUY")).upper()
        signed_qty = qty if side == "BUY" else -qty

        row = aggregate.setdefault(symbol, {"qty": 0, "cost": 0.0})
        row["qty"] += signed_qty
        row["cost"] += signed_qty * price

    positions = []
    for symbol, row in aggregate.items():
        qty = int(row["qty"])
        if qty == 0:
            continue
        avg_entry = abs(row["cost"] / qty) if qty else 0.0
        positions.append(
            {
                "symbol": symbol,
                "qty": qty,
                "avg_entry": avg_entry,
                "profile": "UNKNOWN",
                "strategy": "",
                "source": "paper_trades.jsonl",
                "metadata": {},
            }
        )

    equity = _estimate_equity(positions)
    return PortfolioSnapshot(
        positions=positions,
        cash=0.0,
        equity=equity,
        source="paper_trades.jsonl",
        metadata={"available": True, "path": str(path)},
    )


def merge_snapshots(snapshots: Iterable[PortfolioSnapshot]) -> PortfolioSnapshot:
    positions = []
    sources = []

    for snapshot in snapshots:
        if not snapshot:
            continue
        positions.extend(snapshot.positions)
        sources.append(snapshot.source)

    return PortfolioSnapshot(
        positions=positions,
        cash=0.0,
        equity=_estimate_equity(positions),
        source="+".join(sources) if sources else "NONE",
        metadata={"merged_sources": sources},
    )


def _positions_from_mapping(raw: Mapping[str, Any], source: str) -> List[Dict[str, Any]]:
    positions = []

    for symbol, value in raw.items():
        if not isinstance(value, Mapping):
            continue

        qty = _safe_int(value.get("qty", value.get("net_qty", 0)))
        avg_entry = _safe_float(value.get("avg_entry", value.get("avg_price", value.get("entry_price", 0.0))))

        positions.append(
            {
                "symbol": str(value.get("symbol", symbol)),
                "qty": qty,
                "avg_entry": avg_entry,
                "profile": str(value.get("profile", "UNKNOWN")),
                "strategy": str(value.get("strategy", "")),
                "side": value.get("side"),
                "source": source,
                "metadata": {
                    key: val
                    for key, val in value.items()
                    if key
                    not in {
                        "symbol",
                        "qty",
                        "net_qty",
                        "avg_entry",
                        "avg_price",
                        "entry_price",
                        "profile",
                        "strategy",
                        "side",
                    }
                },
            }
        )

    return positions


def _estimate_equity(positions: List[Dict[str, Any]]) -> float:
    total = 0.0
    for position in positions:
        total += abs(_safe_int(position.get("qty", 0)) * _safe_float(position.get("avg_entry", 0.0)))
    return total


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
