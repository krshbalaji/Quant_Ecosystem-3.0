from enum import Enum


class MarketRegime(Enum):

    NORMAL = "NORMAL"

    VOLATILE = "VOLATILE"

    CRISIS = "CRISIS"

    TRENDING = "TRENDING"

    LOW_LIQUIDITY = (
        "LOW_LIQUIDITY"
    )

    RISK_OFF = "RISK_OFF"