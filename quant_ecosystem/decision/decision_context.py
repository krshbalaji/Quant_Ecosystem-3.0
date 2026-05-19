from dataclasses import dataclass
from typing import Optional

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.discipline import DisciplineDecision
from quant_ecosystem.profiles.base_profile import BaseProfile
from quant_ecosystem.risk.capital_allocator_v2 import CapitalAllocatorV2
from quant_ecosystem.risk.correlation_guard import CorrelationGuard
from quant_ecosystem.risk.reserve_manager import ReserveManager


@dataclass
class DecisionContext:
    profile: BaseProfile
    discipline_decision: DisciplineDecision
    capital_allocator: Optional[CapitalAllocatorV2] = None
    reserve_manager: Optional[ReserveManager] = None
    correlation_guard: Optional[CorrelationGuard] = None
    portfolio_exposure_pct: float = 0.0
    symbol_exposure_pct: float = 0.0
    market_regime: str = "NEUTRAL"
    risk_state: str = "GREEN"
    reserve_allowed: bool = False
    is_premium_opportunity: bool = False
