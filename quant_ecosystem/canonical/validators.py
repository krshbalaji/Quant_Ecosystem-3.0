"""
QE3 Canonical Validators
Pack19 — Unified Data Canonicalization Layer
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

from quant_ecosystem.canonical.exceptions import (
    SchemaValidationError,
    TypeCoercionError,
    TimestampNormalizationError,
)


VALID_ORDER_STATUSES = {
    "PENDING",
    "OPEN",
    "PARTIAL",
    "FILLED",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
}

VALID_SIDES = {
    "BUY",
    "SELL",
}

VALID_MARKETS = {
    "INDIA",
    "US",
    "GLOBAL",
    "CRYPTO",
}

VALID_ASSET_CLASSES = {
    "EQUITY",
    "OPTIONS",
    "FUTURES",
    "CRYPTO",
    "FOREX",
    "ETF",
    "INDEX",
}


def ensure_not_none(value: Any, field_name: str):
    if value is None:
        raise SchemaValidationError(
            f"Field '{field_name}' cannot be None"
        )
    return value


def ensure_positive_number(
    value: Any,
    field_name: str,
    allow_zero: bool = True,
):
    num = to_float(value, field_name)

    if allow_zero:
        if num < 0:
            raise SchemaValidationError(
                f"Field '{field_name}' must be >= 0"
            )
    else:
        if num <= 0:
            raise SchemaValidationError(
                f"Field '{field_name}' must be > 0"
            )

    return num


def ensure_enum(
    value: str,
    allowed: Iterable[str],
    field_name: str,
):
    if value is None:
        raise SchemaValidationError(
            f"Field '{field_name}' missing"
        )

    normalized = str(value).upper().strip()

    if normalized not in allowed:
        raise SchemaValidationError(
            f"Invalid {field_name}: {value}"
        )

    return normalized


def validate_market(market: str):
    return ensure_enum(
        market,
        VALID_MARKETS,
        "market",
    )


def validate_asset_class(asset_class: str):
    return ensure_enum(
        asset_class,
        VALID_ASSET_CLASSES,
        "asset_class",
    )


def validate_order_status(status: str):
    return ensure_enum(
        status,
        VALID_ORDER_STATUSES,
        "order_status",
    )


def validate_side(side: str):
    return ensure_enum(
        side,
        VALID_SIDES,
        "side",
    )


def to_float(
    value: Any,
    field_name: str,
    default: Optional[float] = None,
):
    if value is None:
        if default is not None:
            return default
        raise TypeCoercionError(
            f"Field '{field_name}' cannot convert None to float"
        )

    try:
        return float(value)
    except Exception as exc:
        raise TypeCoercionError(
            f"Cannot convert field '{field_name}' to float: {value}"
        ) from exc


def to_int(
    value: Any,
    field_name: str,
    default: Optional[int] = None,
):
    if value is None:
        if default is not None:
            return default
        raise TypeCoercionError(
            f"Field '{field_name}' cannot convert None to int"
        )

    try:
        return int(value)
    except Exception as exc:
        raise TypeCoercionError(
            f"Cannot convert field '{field_name}' to int: {value}"
        ) from exc


def to_decimal(
    value: Any,
    field_name: str,
):
    if value is None:
        raise TypeCoercionError(
            f"Field '{field_name}' cannot convert None to Decimal"
        )

    try:
        return Decimal(str(value))
    except Exception as exc:
        raise TypeCoercionError(
            f"Cannot convert field '{field_name}' to Decimal: {value}"
        ) from exc


def normalize_timestamp(value: Any):
    if value is None:
        return datetime.utcnow()

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except Exception as exc:
            raise TimestampNormalizationError(
                f"Invalid epoch timestamp: {value}"
            ) from exc

    if isinstance(value, str):
        value = value.strip()

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue

    raise TimestampNormalizationError(
        f"Unsupported timestamp format: {value}"
    )


def ensure_string(
    value: Any,
    field_name: str,
    allow_empty: bool = False,
):
    if value is None:
        raise SchemaValidationError(
            f"Field '{field_name}' missing"
        )

    s = str(value)

    if not allow_empty and not s.strip():
        raise SchemaValidationError(
            f"Field '{field_name}' empty"
        )

    return s.strip()