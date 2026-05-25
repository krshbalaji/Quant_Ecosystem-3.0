from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ResearchHypothesis:
    hypothesis_id: str
    title: str
    thesis: str
    asset_class: str = "EQUITY"
    metadata: Dict = field(
        default_factory=dict
    )


@dataclass
class TechnicalSignal:
    symbol: str
    signal_type: str
    direction: str
    confidence: float
    timeframe: str = "1D"
    metadata: Dict = field(
        default_factory=dict
    )


@dataclass
class FactorSignal:
    symbol: str
    factor_name: str
    score: float
    confidence: float
    metadata: Dict = field(
        default_factory=dict
    )


@dataclass
class AlphaSignal:
    symbol: str
    direction: str
    confidence: float
    source_signals: List = field(
        default_factory=list
    )
    metadata: Dict = field(
        default_factory=dict
    )


@dataclass
class RankedOpportunity:
    symbol: str
    alpha_score: float
    confidence: float
    rank: Optional[int] = None
    metadata: Dict = field(
        default_factory=dict
    )