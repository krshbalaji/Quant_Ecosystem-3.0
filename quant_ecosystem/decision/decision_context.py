from dataclasses import dataclass
from typing import Any, Dict, Optional

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.discipline import DisciplineDecision
from quant_ecosystem.intelligence.regime_memory import RegimeMemory
from quant_ecosystem.intelligence.regime_service import RegimeService
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
    legacy_regime: str = "UNKNOWN"
    regime_confidence: float = 0.0
    regime_mode: str = "STABLE"
    transition_alert: bool = False
    transition_score: float = 0.0
    transition_type: str = "NONE"
    regime_details: Optional[Dict[str, Any]] = None
    regime_memory: Optional[RegimeMemory] = None
    risk_state: str = "GREEN"
    reserve_allowed: bool = False
    is_premium_opportunity: bool = False
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_regime_inputs(
        cls,
        profile: BaseProfile,
        discipline_decision: DisciplineDecision,
        regime_service: Optional[RegimeService] = None,
        timeframe_data: Optional[Dict[str, Dict]] = None,
        extra_signals: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "DecisionContext":
        service = regime_service or RegimeService()
        payload = service.analyze(timeframe_data=timeframe_data, extra_signals=extra_signals)
        return cls(
            profile=profile,
            discipline_decision=discipline_decision,
            market_regime=payload.get("regime_v2", payload.get("regime", "UNKNOWN")),
            legacy_regime=payload.get("legacy_regime", payload.get("regime", "UNKNOWN")),
            regime_confidence=payload.get("regime_confidence", 0.0),
            regime_mode=payload.get("regime_mode", "STABLE"),
            transition_alert=payload.get("transition_alert", False),
            transition_score=payload.get("transition_score", 0.0),
            transition_type=payload.get("transition_type", "NONE"),
            regime_details=payload.get("regime_details", {}),
            **kwargs,
        )
