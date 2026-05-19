from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Union

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.portfolio.position_health import HealthState, assess_position_health
from quant_ecosystem.portfolio.thesis_lifecycle import infer_lifecycle


@dataclass
class PortfolioSnapshot:
    positions: Dict[str, Position] = field(default_factory=dict)

    @classmethod
    def from_positions(cls, positions: Iterable[Union[Position, Dict[str, Any]]]) -> "PortfolioSnapshot":
        normalized: Dict[str, Position] = {}
        for position in positions:
            pos = position if isinstance(position, Position) else Position.from_mapping(position)
            normalized[pos.symbol] = pos
        return cls(positions=normalized)

    def summary(self, trend_proxy_map: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        total_unrealized_pnl = 0.0
        total_realized_pnl = 0.0
        total_holding_days = 0.0
        trend_sum = 0.0
        health_counts: Dict[str, int] = {}
        lifecycle_counts: Dict[str, int] = {}

        if not self.positions:
            return {
                "position_count": 0,
                "total_unrealized_pnl": 0.0,
                "total_realized_pnl": 0.0,
                "average_holding_days": 0.0,
                "average_trend_proxy": 0.0,
                "health_counts": health_counts,
                "lifecycle_counts": lifecycle_counts,
            }

        for position in self.positions.values():
            total_unrealized_pnl += float(position.pnl_unrealized)
            total_realized_pnl += float(position.pnl_realized)
            holding_days = float(position.metadata.get("holding_days", 0.0) or 0.0)
            total_holding_days += holding_days
            trend_proxy = float(
                (trend_proxy_map or {}).get(position.symbol, position.metadata.get("trend_proxy", 0.0)) or 0.0
            )
            trend_sum += trend_proxy

            health = assess_position_health(position, trend_proxy=trend_proxy)
            lifecycle = infer_lifecycle(position)
            health_counts[health.value] = health_counts.get(health.value, 0) + 1
            lifecycle_counts[lifecycle.value] = lifecycle_counts.get(lifecycle.value, 0) + 1

        position_count = len(self.positions)
        return {
            "position_count": position_count,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_realized_pnl": total_realized_pnl,
            "average_holding_days": round(total_holding_days / position_count, 2),
            "average_trend_proxy": round(trend_sum / position_count, 3),
            "health_counts": health_counts,
            "lifecycle_counts": lifecycle_counts,
        }
