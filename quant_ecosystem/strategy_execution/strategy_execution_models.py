from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class StrategyRiskBudget:
    strategy_id: str

    max_capital: float = 0.0
    max_positions: int = 0
    max_loss: float = 0.0

    current_capital_used: float = 0.0
    current_positions: int = 0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    metadata: Dict = field(default_factory=dict)

    @property
    def total_pnl(self):
        return (
            self.realized_pnl
            + self.unrealized_pnl
        )

    @property
    def remaining_capital(self):
        return max(
            0.0,
            self.max_capital
            - self.current_capital_used,
        )


@dataclass
class StrategyExecutionIntent:
    strategy_id: str

    symbol: str
    side: str
    qty: float

    order_type: str = "MARKET"
    price: Optional[float] = None

    broker: Optional[str] = None
    market: Optional[str] = None

    confidence: float = 0.0
    priority: int = 100

    trade_type: str = "DIRECTIONAL"

    metadata: Dict = field(default_factory=dict)

    def execution_notional(self):
        px = float(self.price or 0.0)

        return (
            float(self.qty)
            * px
        )