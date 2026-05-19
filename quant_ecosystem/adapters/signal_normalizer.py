from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import SignalIntent


SIDE_ALIASES = {
    "BUY": "BUY",
    "B": "BUY",
    "LONG": "BUY",
    "ENTRY_LONG": "BUY",
    "BUY_TO_OPEN": "BUY",
    "ACCUMULATE": "BUY",
    "SELL": "SELL",
    "S": "SELL",
    "SHORT": "SELL",
    "ENTRY_SHORT": "SELL",
    "SELL_TO_OPEN": "SELL",
    "EXIT_LONG": "SELL",
    "CLOSE_LONG": "SELL",
    "EXIT_SHORT": "BUY",
    "CLOSE_SHORT": "BUY",
}


SOURCE_ALIASES = {
    "TV": "TRADINGVIEW",
    "TRADING_VIEW": "TRADINGVIEW",
    "TRADINGVIEW": "TRADINGVIEW",
    "STRATEGY": "STRATEGY_BRAIN",
    "STRATEGY_BRAIN": "STRATEGY_BRAIN",
    "AI": "AI_SIGNAL",
    "AI_ENGINE": "AI_SIGNAL",
    "AI_SIGNAL": "AI_SIGNAL",
    "MANUAL": "MANUAL",
    "TELEGRAM": "MANUAL",
}


DEFAULTS = {
    "TRADINGVIEW": {
        "profile": ProfileTypes.INTRADAY,
        "strategy": "TRADINGVIEW",
        "horizon": "SHORT_TERM",
    },
    "STRATEGY_BRAIN": {
        "profile": ProfileTypes.SCALP,
        "strategy": "STRATEGY_BRAIN",
        "horizon": "SHORT_TERM",
    },
    "AI_SIGNAL": {
        "profile": ProfileTypes.INTRADAY,
        "strategy": "AI_ENGINE",
        "horizon": "SHORT_TERM",
    },
    "MANUAL": {
        "profile": ProfileTypes.INTRADAY,
        "strategy": "MANUAL",
        "horizon": "MANUAL",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_present(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_source(source: str) -> str:
    key = str(source or "UNKNOWN").strip().upper().replace(" ", "_").replace("-", "_")
    return SOURCE_ALIASES.get(key, key)


def _normalize_side(value: Any) -> str:
    key = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    side = SIDE_ALIASES.get(key)

    if not side:
        raise ValueError("side/action must resolve to BUY or SELL")

    return side


def _normalize_profile(value: Any, default: ProfileTypes | str) -> ProfileTypes | str:
    if value in (None, ""):
        return default

    if isinstance(value, ProfileTypes):
        return value

    key = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    if key == "F&O":
        key = "FNO"

    try:
        return ProfileTypes(key)
    except ValueError:
        return key


def _normalize_confidence(value: Any) -> float:
    if value in (None, ""):
        return 0.0

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0

    if confidence > 1.0:
        confidence = confidence / 100.0 if confidence <= 100.0 else 1.0

    return max(0.0, min(confidence, 1.0))


def _normalize_timestamp(value: Any) -> str:
    if value in (None, ""):
        return _utc_now()

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    raw = str(value).strip()
    try:
        timestamp = float(raw)
    except ValueError:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc).isoformat()

    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _normalize_symbol(value: Any) -> str:
    if value in (None, ""):
        raise ValueError("symbol is required")

    symbol = str(value).strip().upper()

    if ":" in symbol:
        symbol = symbol.split(":", 1)[1]

    if symbol.endswith(".P"):
        symbol = symbol[:-2]

    if symbol.endswith("PERP"):
        symbol = symbol[:-4]

    if symbol.endswith("!"):
        symbol = symbol[:-1]

    if symbol.endswith(".NS"):
        return symbol

    if symbol.endswith("-EQ"):
        symbol = symbol[:-3]

    if "-" in symbol and not symbol.startswith("NSE-"):
        symbol = symbol.replace("-", "")

    cleaned = []
    for ch in symbol:
        if ch.isalnum() or ch in {".", "_"}:
            cleaned.append(ch)

    symbol = "".join(cleaned).strip("._")

    if not symbol:
        raise ValueError("symbol is required")

    return symbol


def _metadata(raw: Mapping[str, Any], source: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metadata = {
        "raw": dict(raw),
        "normalized_source": source,
    }

    if extra:
        metadata.update(extra)

    return metadata


def _build_signal(
    raw: Mapping[str, Any],
    source: str,
    default_profile: ProfileTypes | str,
    default_strategy: str,
    default_horizon: str,
) -> SignalIntent:
    symbol = _normalize_symbol(_first_present(raw, "symbol", "ticker", "tickerid", "instrument", "s"))
    side = _normalize_side(_first_present(raw, "side", "action", "signal", "order_action", "direction"))
    profile = _normalize_profile(_first_present(raw, "profile", "trade_profile"), default_profile)
    strategy = str(_first_present(raw, "strategy", "strategy_name", "engine", default=default_strategy)).upper()
    confidence = _normalize_confidence(_first_present(raw, "confidence", "score", "strength", default=0.0))
    horizon = str(_first_present(raw, "horizon", "time_horizon", "holding_period", default=default_horizon)).upper()
    timestamp = _normalize_timestamp(_first_present(raw, "timestamp", "ts", "time", "alert_time", "created_at"))

    return SignalIntent(
        symbol=symbol,
        side=side,
        profile=profile,
        strategy=strategy,
        confidence=confidence,
        horizon=horizon,
        source=source,
        timestamp=timestamp,
        metadata=_metadata(raw, source),
    )


def normalize(raw: Mapping[str, Any], source: str) -> SignalIntent:
    normalized_source = _normalize_source(source)

    if normalized_source == "TRADINGVIEW":
        return normalize_tradingview(raw)

    if normalized_source == "STRATEGY_BRAIN":
        return normalize_strategy_brain(raw)

    if normalized_source == "AI_SIGNAL":
        return normalize_ai_signal(raw)

    if normalized_source == "MANUAL":
        return normalize_manual_signal(raw)

    defaults = {
        "profile": ProfileTypes.INTRADAY,
        "strategy": normalized_source,
        "horizon": "UNKNOWN",
    }
    return _build_signal(
        raw=raw,
        source=normalized_source,
        default_profile=defaults["profile"],
        default_strategy=defaults["strategy"],
        default_horizon=defaults["horizon"],
    )


def normalize_tradingview(raw: Mapping[str, Any]) -> SignalIntent:
    defaults = DEFAULTS["TRADINGVIEW"]
    return _build_signal(
        raw=raw,
        source="TRADINGVIEW",
        default_profile=defaults["profile"],
        default_strategy=defaults["strategy"],
        default_horizon=defaults["horizon"],
    )


def normalize_strategy_brain(raw: Mapping[str, Any]) -> SignalIntent:
    defaults = DEFAULTS["STRATEGY_BRAIN"]
    return _build_signal(
        raw=raw,
        source="STRATEGY_BRAIN",
        default_profile=defaults["profile"],
        default_strategy=defaults["strategy"],
        default_horizon=defaults["horizon"],
    )


def normalize_ai_signal(raw: Mapping[str, Any]) -> SignalIntent:
    defaults = DEFAULTS["AI_SIGNAL"]
    return _build_signal(
        raw=raw,
        source="AI_SIGNAL",
        default_profile=defaults["profile"],
        default_strategy=defaults["strategy"],
        default_horizon=defaults["horizon"],
    )


def normalize_manual_signal(raw: Mapping[str, Any]) -> SignalIntent:
    defaults = DEFAULTS["MANUAL"]
    return _build_signal(
        raw=raw,
        source="MANUAL",
        default_profile=defaults["profile"],
        default_strategy=defaults["strategy"],
        default_horizon=defaults["horizon"],
    )
