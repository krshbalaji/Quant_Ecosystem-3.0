import os
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from telegram_control import process_callbacks, send_message, start_trade_panel
from quant_ecosystem.adapters.signal_normalizer import normalize_tradingview
from quant_ecosystem.contracts.order_intent import OrderIntent
from quant_ecosystem.execution.unified_broker_router import submit as submit_order
from quant_ecosystem.storage.signal_store import record_signal

load_dotenv()

app = Flask(__name__)


WEBHOOK_SECRET = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", os.getenv("WEBHOOK_SECRET", "QE3_SECRET"))
BROKER_MODE = os.getenv("TRADINGVIEW_BROKER_MODE", os.getenv("BROKER_MODE", "paper"))
DEFAULT_QTY = int(os.getenv("TRADINGVIEW_DEFAULT_QTY", "1"))
EXECUTION_ENABLED = os.getenv("TRADINGVIEW_EXECUTION_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
APPROVAL_ENABLED = os.getenv(
    "TRADINGVIEW_APPROVAL_ENABLED",
    os.getenv("TRADINGVIEW_REQUIRE_APPROVAL", "true"),
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}
APPROVAL_WORKER_ENABLED = os.getenv("TRADINGVIEW_APPROVAL_WORKER", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
APPROVAL_POLL_SECONDS = float(os.getenv("TRADINGVIEW_APPROVAL_POLL_SECONDS", "3"))
REPLAY_WINDOW_SECONDS = int(os.getenv("TRADINGVIEW_REPLAY_WINDOW_SECONDS", "120"))
DUPLICATE_TTL_SECONDS = int(os.getenv("TRADINGVIEW_DUPLICATE_TTL_SECONDS", "120"))
APPROVAL_TIMEOUT_SECONDS = int(os.getenv("TRADINGVIEW_APPROVAL_TIMEOUT_SECONDS", "300"))

SIDE_ALIASES = {
    "BUY": "BUY",
    "B": "BUY",
    "LONG": "BUY",
    "ENTRY_LONG": "BUY",
    "BUY_TO_OPEN": "BUY",
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

SUPPORTED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"}

PENDING_SIGNALS: Dict[str, "PendingApproval"] = {}
DUPLICATE_CACHE: Dict[str, float] = {}
NONCE_CACHE: Dict[str, float] = {}
_approval_worker_started = False
_approval_worker_lock = threading.Lock()
SECRET_FIELDS = {"secret", "token", "passphrase"}


@dataclass
class NormalizedSignal:
    symbol: str
    side: str
    qty: int
    time_bucket: int
    entry: Any = "MARKET"
    confidence: float = 0.0
    source: str = "TRADINGVIEW"
    strategy: str = "TRADINGVIEW"
    timestamp: float = 0.0
    nonce: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class PendingApproval:
    signal: NormalizedSignal
    expires_at: float


def _first_present(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_side(value: Any) -> Optional[str]:
    if value is None:
        return None

    side = str(value).strip().upper().replace(" ", "_").replace("-", "_")
    return SIDE_ALIASES.get(side)


def _normalize_qty(value: Any) -> int:
    if value in (None, ""):
        return DEFAULT_QTY

    try:
        qty = int(float(value))
    except (TypeError, ValueError):
        raise ValueError("qty must be numeric")

    if qty < 1:
        raise ValueError("qty must be at least 1")

    return qty


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

    symbol = "".join(ch for ch in symbol if ch.isalnum())

    if not symbol:
        raise ValueError("symbol is required")

    return symbol


def _normalize_confidence(value: Any) -> float:
    if value in (None, ""):
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_entry(value: Any) -> Any:
    if value in (None, ""):
        return "MARKET"

    if isinstance(value, str) and value.strip().upper() == "MARKET":
        return "MARKET"

    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def validate_secret(data: Dict[str, Any]) -> bool:
    supplied = (
        request.headers.get("X-TradingView-Secret")
        or request.headers.get("X-TV-Secret")
        or request.headers.get("X-Webhook-Secret")
        or data.get("secret")
        or data.get("token")
        or data.get("passphrase")
    )
    return bool(WEBHOOK_SECRET) and supplied == WEBHOOK_SECRET


def sanitized_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if str(key).lower() not in SECRET_FIELDS
    }


def parse_alert_timestamp(data: Dict[str, Any]) -> float:
    value = _first_present(data, "timestamp", "ts", "time", "alert_time", "t")

    if value in (None, ""):
        raise ValueError("timestamp is required")

    if isinstance(value, (int, float)):
        timestamp = float(value)
    else:
        raw = str(value).strip()
        try:
            timestamp = float(raw)
        except ValueError:
            normalized = raw.replace("Z", "+00:00")
            timestamp = datetime.fromisoformat(normalized).timestamp()

    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000

    now = time.time()
    age = now - timestamp

    if age > REPLAY_WINDOW_SECONDS:
        raise ValueError("timestamp is too old")

    if age < -REPLAY_WINDOW_SECONDS:
        raise ValueError("timestamp is too far in the future")

    return timestamp


def _cleanup_expiring_cache(cache: Dict[str, float], now: Optional[float] = None) -> None:
    now = now or time.time()
    expired = [key for key, expires_at in cache.items() if expires_at <= now]

    for key in expired:
        cache.pop(key, None)


def expire_pending_approvals(now: Optional[float] = None) -> None:
    now = now or time.time()

    expired_keys = [
        key
        for key, pending in PENDING_SIGNALS.items()
        if pending.expires_at <= now
    ]

    for key in expired_keys:
        pending = PENDING_SIGNALS.pop(key, None)
        if pending:
            log_event(pending.signal, "rejected", reason="approval_timeout")
            send_message(
                f"TradingView approval expired: "
                f"{pending.signal.side} {pending.signal.qty} {pending.signal.symbol}"
            )

def validate_nonce(data: Dict[str, Any]) -> Optional[str]:
    nonce = _first_present(data, "nonce", "alert_id", "id")

    if nonce in (None, ""):
        return None

    nonce = str(nonce).strip()
    now = time.time()
    _cleanup_expiring_cache(NONCE_CACHE, now)

    if nonce in NONCE_CACHE:
        raise ValueError("duplicate nonce")

    NONCE_CACHE[nonce] = now + REPLAY_WINDOW_SECONDS
    return nonce


def create_fingerprint(signal: NormalizedSignal) -> str:
    return "|".join(
        [
            signal.symbol,
            signal.side,
            signal.strategy,
            str(signal.qty),
            str(signal.timestamp),
            str(signal.nonce or "NO_NONCE"),
        ]
    )


def check_duplicate(signal: NormalizedSignal) -> Optional[str]:
    now = time.time()
    _cleanup_expiring_cache(DUPLICATE_CACHE, now)

    fingerprint = create_fingerprint(signal)

    if fingerprint in DUPLICATE_CACHE:
        return fingerprint

    DUPLICATE_CACHE[fingerprint] = now + DUPLICATE_TTL_SECONDS
    return None


def log_event(
    signal: Optional[NormalizedSignal],
    decision: str,
    reason: Optional[str] = None,
    duplicate: bool = False,
) -> None:
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "symbol": signal.symbol if signal else None,
        "side": signal.side if signal else None,
        "qty": signal.qty if signal else None,
        "source": signal.source if signal else "TRADINGVIEW",
        "decision": decision,
        "duplicate": duplicate,
    }

    if reason:
        event["reason"] = reason

    print(json.dumps(event, separators=(",", ":")))


def signal_to_dict(signal: NormalizedSignal) -> Dict[str, Any]:
    data = {
        "symbol": signal.symbol,
        "side": signal.side,
        "qty": signal.qty,
        "entry": signal.entry,
        "confidence": signal.confidence,
        "source": signal.source,
        "strategy": signal.strategy,
        "timestamp": signal.timestamp,
        "nonce": signal.nonce,
    }

    if signal.raw:
        data["raw"] = {
            key: value
            for key, value in signal.raw.items()
            if str(key).lower() not in SECRET_FIELDS
        }

    return data


def normalize_signal(data: Dict[str, Any]) -> NormalizedSignal:
    timestamp = parse_alert_timestamp(data)
    nonce = validate_nonce(data)
    canonical = normalize_tradingview(sanitized_payload(data))
    symbol = canonical.symbol
    side = canonical.side
    qty = _normalize_qty(_first_present(data, "qty", "quantity", "contracts", "shares"))
    entry = _normalize_entry(_first_present(data, "entry", "price", "close", "order_price", default="MARKET"))
    confidence = canonical.confidence
    source = canonical.source
    strategy = canonical.strategy

    if side not in {"BUY", "SELL"}:
        raise ValueError("side/action must resolve to BUY or SELL")

    return NormalizedSignal(
        symbol=symbol,
        side=side,
        qty=qty,
        time_bucket=int(timestamp // DUPLICATE_TTL_SECONDS),
        entry=entry,
        confidence=confidence,
        source=source,
        strategy=strategy,
        timestamp=timestamp,
        nonce=nonce,
        raw=sanitized_payload(data),
    )


def record_canonical_signal(signal: NormalizedSignal) -> str:
    canonical = normalize_tradingview(signal.raw or {})
    return record_signal(canonical)


def execute_signal(signal: NormalizedSignal) -> Dict[str, Any]:
    if os.getenv("GLOBAL_KILL_SWITCH", "").lower() in {"1", "true", "yes", "on"}:
        log_event(signal, "rejected", reason="global_kill_switch")
        return {
            "status": "rejected",
            "reason": "GLOBAL_KILL_SWITCH_ACTIVE",
        }

    if not EXECUTION_ENABLED:
        log_event(signal, "rejected", reason="execution_disabled")
        return {
            "status": "rejected",
            "reason": "EXECUTION_DISABLED",
        }

    order = OrderIntent(
        symbol=signal.symbol,
        side=signal.side,
        qty=signal.qty,
        order_type="MARKET" if signal.entry == "MARKET" else "LIMIT",
        profile="INTRADAY",
        reason="TRADINGVIEW_SIGNAL",
        approval_id=signal.nonce or create_fingerprint(signal),
        source=signal.source,
        metadata={
            "strategy": signal.strategy,
            "entry": signal.entry,
            "confidence": signal.confidence,
            "timestamp": signal.timestamp,
            "approval_ts": time.time(),
        },
    )

    result = submit_order(order, mode=BROKER_MODE)

    decision = "executed" if result.get("ok") else "rejected"
    log_event(signal, decision, reason=result.get("reason"))

    return {
        "status": decision,
        "broker_mode": BROKER_MODE,
        "signal": signal_to_dict(signal),
        "execution_result": result,
    }


def queue_for_telegram_approval(signal: NormalizedSignal) -> Dict[str, Any]:
    expire_pending_approvals()

    fingerprint = create_fingerprint(signal)

    PENDING_SIGNALS[fingerprint] = PendingApproval(
        signal=signal,
        expires_at=time.time() + APPROVAL_TIMEOUT_SECONDS,
    )

    start_trade_panel(
        symbol=signal.symbol,
        side=signal.side,
        entry=signal.entry,
        regime=signal.source,
    )

    log_event(signal, "queued")

    return {
        "status": "queued",
        "approval": "telegram",
        "approval_expires_in_sec": APPROVAL_TIMEOUT_SECONDS,
        "fingerprint": fingerprint,
        "signal": signal_to_dict(signal),
    }


def handle_telegram_decision() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    expire_pending_approvals()

    if os.getenv("GLOBAL_KILL_SWITCH", "").lower() in {"1", "true", "yes", "on"}:
        return "BLOCKED", {"status": "blocked", "reason": "GLOBAL_KILL_SWITCH_ACTIVE"}

    action, state = process_callbacks()

    if action == "CANCEL":
        symbol = state.get("symbol") if state else None
        fingerprint = state.get("fingerprint") if state else None

        pending = None
        if fingerprint:
            pending = PENDING_SIGNALS.pop(fingerprint, None)

        elif symbol:
            for key, candidate in list(PENDING_SIGNALS.items()):
                if candidate.signal.symbol == symbol:
                    pending = PENDING_SIGNALS.pop(key, None)
                    break

        if pending:
            log_event(pending.signal, "rejected", reason="cancelled")

        send_message("Trade cancelled from Telegram.")
        return action, {"status": "cancelled", "symbol": symbol}

    if action != "EXECUTE" or not state:
        return action, None

    fingerprint = state.get("fingerprint")
    pending = PENDING_SIGNALS.pop(fingerprint, None) if fingerprint else None
    pending_signal = pending.signal if pending else None

    if not pending_signal:
        send_message("Trade rejected: approval context missing.")
        return action, {"status": "rejected", "reason": "approval context missing"}

    signal = pending_signal

    if not EXECUTION_ENABLED:
        log_event(signal, "approved", reason="execution_disabled")
        send_message("TradingView signal approved. Execution is disabled.")
        return action, {
            "status": "approved",
            "execution": "disabled",
            "signal": signal_to_dict(signal),
        }

    send_message("Executing approved TradingView trade...")
    result = execute_signal(signal)
    send_message(f"Trade executed: {signal.side} {signal.qty} {signal.symbol}")
    return action, result

@app.route("/tv-webhook", methods=["POST"])
@app.route("/tradingview-webhook", methods=["POST"])
def tv_webhook():
    expire_pending_approvals()
    data = request.get_json(silent=True)

    if os.getenv("GLOBAL_KILL_SWITCH", "").lower() in {"1", "true", "yes", "on"}:
        log_event(None, "rejected", reason="global_kill_switch")
        return jsonify({"status": "error", "msg": "GLOBAL_KILL_SWITCH_ACTIVE"}), 503

    if not isinstance(data, dict):
        log_event(None, "rejected", reason="invalid_json")
        return jsonify({"status": "error", "msg": "invalid or empty JSON payload"}), 400

    if not WEBHOOK_SECRET or WEBHOOK_SECRET == "QE3_SECRET":
        log_event(None, "rejected", reason="unsafe_secret_configuration")
        return jsonify({"status": "error", "msg": "unsafe webhook secret configuration"}), 503

    if not validate_secret(data):
        log_event(None, "rejected", reason="invalid_secret")
        return jsonify({"status": "error", "msg": "invalid secret"}), 403

    try:
        signal = normalize_signal(data)
    except ValueError as exc:
        log_event(None, "rejected", reason=str(exc))
        return jsonify({"status": "error", "msg": str(exc)}), 400

    duplicate_fingerprint = check_duplicate(signal)
    if duplicate_fingerprint:
        log_event(signal, "duplicate", reason="duplicate_alert", duplicate=True)
        return jsonify(
            {
                "status": "duplicate",
                "msg": "duplicate alert suppressed",
                "fingerprint": duplicate_fingerprint,
                "signal": signal_to_dict(signal),
            }
        ), 409

    try:
        signal_id = record_canonical_signal(signal)

        response = {
            "status": "recorded",
            "signal_id": signal_id,
            "signal": signal_to_dict(signal),
            "execution_enabled": EXECUTION_ENABLED,
            "approval_enabled": APPROVAL_ENABLED,
        }

        log_event(signal, "recorded")

        if APPROVAL_ENABLED:
            response = queue_for_telegram_approval(signal)
            response["signal_id"] = signal_id
            response["execution_enabled"] = EXECUTION_ENABLED

        elif EXECUTION_ENABLED:
            response = execute_signal(signal)
            response["signal_id"] = signal_id

    except Exception as exc:
        log_event(signal, "rejected", reason=str(exc))
        return jsonify({"status": "error", "msg": str(exc)}), 500

    return jsonify(response)


if __name__ == "__main__":
    start_approval_worker()
    app.run(
        host=os.getenv("TRADINGVIEW_BRIDGE_HOST", "0.0.0.0"),
        port=int(os.getenv("TRADINGVIEW_BRIDGE_PORT", "5005")),
        use_reloader=False,
    )
