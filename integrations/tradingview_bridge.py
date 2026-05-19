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
from quant_ecosystem.decision import ArbitrationAction, ArbitrationEngine, DecisionContext
from quant_ecosystem.discipline import (
    DisciplineAction,
    DisciplineDecision,
    DisciplineGovernor,
    DisciplineState,
)
from quant_ecosystem.execution.unified_broker_router import submit as submit_order
from quant_ecosystem.intelligence.regime_service import RegimeService
from quant_ecosystem.portfolio.portfolio_watchdog import PortfolioWatchdog
from quant_ecosystem.profiles import get_profile
from quant_ecosystem.risk.capital_allocator_v2 import CapitalAllocatorV2
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
    metadata: Optional[Dict[str, Any]] = None
    profile: str = "SCALP"


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
    expired_symbols = [
        symbol
        for symbol, pending in PENDING_SIGNALS.items()
        if pending.expires_at <= now
    ]

    for symbol in expired_symbols:
        pending = PENDING_SIGNALS.pop(symbol, None)
        if pending:
            log_event(pending.signal, "rejected", reason="approval_timeout")
            send_message(f"TradingView approval expired: {pending.signal.side} {pending.signal.qty} {symbol}")


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
            str(signal.time_bucket),
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


def _extract_timeframe_data(signal: NormalizedSignal) -> Dict[str, Any]:
    if isinstance(signal.raw, dict):
        return signal.raw.get("market_data") or signal.raw.get("timeframe_data") or {}
    return {}


def _signal_notional(signal: NormalizedSignal) -> float:
    notional = signal.metadata.get("notional")
    if isinstance(notional, (int, float)):
        return float(notional)
    try:
        return float(signal.qty)
    except (TypeError, ValueError):
        return 1.0


def _build_market_data_payload(context: DecisionContext) -> Dict[str, Any]:
    return {
        "market_regime": context.market_regime,
        "regime_confidence": float(context.regime_confidence or 0.0),
        "transition_alert": bool(context.transition_alert),
        "transition_score": float(context.transition_score or 0.0),
        "transition_type": str(context.transition_type or "NONE").upper(),
    }


def _evaluate_tradingview_signal(signal: NormalizedSignal) -> Dict[str, Any]:
    profile = get_profile(getattr(signal, "profile", "SCALP"))
    regime_service = RegimeService()
    timeframe_data = _extract_timeframe_data(signal)
    extra_signals = {"source": signal.source, "strategy": signal.strategy}
    context = DecisionContext.from_regime_inputs(
        profile=profile,
        discipline_decision=DisciplineDecision(action=DisciplineAction.ALLOW, reason="initial discipline", confidence=0.0),
        regime_service=regime_service,
        timeframe_data=timeframe_data,
        extra_signals=extra_signals,
        portfolio_exposure_pct=0.0,
        symbol_exposure_pct=0.0,
        risk_state="GREEN",
        reserve_allowed=False,
        metadata={
            "bridge": "tradingview",
            "payload_source": "webhook",
        },
    )

    arbitration_decision = ArbitrationEngine().arbitrate([signal], context)
    if arbitration_decision.action != ArbitrationAction.TAKE:
        return {
            "status": "rejected",
            "reason": "arbitration",
            "arbitration": {
                "action": arbitration_decision.action.value,
                "reason": arbitration_decision.reason,
                "details": arbitration_decision.details or {},
            },
            "market_regime": context.market_regime,
            "transition_alert": context.transition_alert,
        }
    discipline_decision = DisciplineGovernor().evaluate(
        signal, profile, DisciplineState(), market_data=_build_market_data_payload(context)
    )
    if discipline_decision.action != DisciplineAction.ALLOW:
        return {
            "status": "blocked",
            "reason": "discipline",
            "discipline": {
                "action": discipline_decision.action.value,
                "reason": discipline_decision.reason,
                "confidence": float(discipline_decision.confidence or 0.0),
                "details": discipline_decision.details,
            },
            "market_regime": context.market_regime,
            "transition_alert": context.transition_alert,
        }
    capital_amount = _signal_notional(signal)
    allocator = CapitalAllocatorV2()
    if not allocator.can_allocate(profile, capital_amount, allow_reserve=False):
        return {
            "status": "blocked",
            "reason": "capital",
            "capital_requested": capital_amount,
            "capital_available": allocator.get_available_budget(profile),
            "market_regime": context.market_regime,
            "transition_alert": context.transition_alert,
        }
    advisory = None
    position_data = None
    if isinstance(signal.raw, dict):
        position_data = signal.raw.get("position") or signal.metadata.get("position")
    if isinstance(position_data, dict):
        try:
            advice = PortfolioWatchdog().recommend_action(position_data)
            advisory = advice.to_dict()
        except Exception:
            advisory = None
    return {
        "status": "ready",
        "market_regime": context.market_regime,
        "regime_confidence": context.regime_confidence,
        "transition_alert": context.transition_alert,
        "transition_score": context.transition_score,
        "transition_type": context.transition_type,
        "arbitration": {
            "action": arbitration_decision.action.value,
            "reason": arbitration_decision.reason,
            "details": arbitration_decision.details or {},
        },
        "discipline": {
            "action": discipline_decision.action.value,
            "reason": discipline_decision.reason,
            "confidence": float(discipline_decision.confidence or 0.0),
            "details": discipline_decision.details,
        },
        "capital_requested": capital_amount,
        "portfolio_advisory": advisory,
    }


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
    profile = str(_first_present(data, "profile", default="SCALP")).upper()

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
        profile=profile,
        metadata={
            "bridge": "tradingview",
            "payload_source": "webhook",
        },
    )


def record_canonical_signal(signal: NormalizedSignal) -> str:
    canonical = normalize_tradingview(signal.raw or {})
    return record_signal(canonical)


def execute_signal(signal: NormalizedSignal) -> Dict[str, Any]:
    order = OrderIntent(
        symbol=signal.symbol,
        side=signal.side,
        qty=signal.qty,
        order_type="MARKET" if signal.entry == "MARKET" else "LIMIT",
        profile="INTRADAY",
        reason="TRADINGVIEW_SIGNAL",
        approval_id=signal.nonce,
        source=signal.source,
        metadata={
            "strategy": signal.strategy,
            "entry": signal.entry,
            "confidence": signal.confidence,
            "timestamp": signal.timestamp,
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
    PENDING_SIGNALS[signal.symbol] = PendingApproval(
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
        "signal": signal_to_dict(signal),
    }


def handle_telegram_decision() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    expire_pending_approvals()
    action, state = process_callbacks()

    if action == "CANCEL":
        symbol = state.get("symbol") if state else None
        pending = PENDING_SIGNALS.pop(symbol, None) if symbol else None
        if pending:
            log_event(pending.signal, "rejected", reason="cancelled")
        send_message("Trade cancelled from Telegram.")
        return action, {"status": "cancelled", "symbol": symbol}

    if action != "EXECUTE" or not state:
        return action, None

    symbol = state.get("symbol")
    pending = PENDING_SIGNALS.pop(symbol, None) if symbol else None
    pending_signal = pending.signal if pending else None
    signal = NormalizedSignal(
        symbol=_normalize_symbol(symbol or (pending_signal.symbol if pending_signal else "")),
        side=state.get("side") or (pending_signal.side if pending_signal else ""),
        qty=_normalize_qty(state.get("qty") or (pending_signal.qty if pending_signal else DEFAULT_QTY)),
        time_bucket=pending_signal.time_bucket if pending_signal else int(time.time() // DUPLICATE_TTL_SECONDS),
        entry=state.get("price") or state.get("entry") or (pending_signal.entry if pending_signal else "MARKET"),
        confidence=pending_signal.confidence if pending_signal else 0.0,
        source=pending_signal.source if pending_signal else "TRADINGVIEW",
        strategy=state.get("strategy") or (pending_signal.strategy if pending_signal else "TRADINGVIEW"),
        profile=pending_signal.profile if pending_signal else "SCALP",
        timestamp=pending_signal.timestamp if pending_signal else time.time(),
        nonce=pending_signal.nonce if pending_signal else None,
        raw=pending_signal.raw if pending_signal else state,
    )

    if not signal.symbol or signal.side not in {"BUY", "SELL"}:
        log_event(signal, "rejected", reason="invalid_approved_signal")
        send_message("Trade rejected: invalid approved signal.")
        return action, {"status": "rejected", "reason": "invalid approved signal"}

    evaluation = _evaluate_tradingview_signal(signal)
    if evaluation["status"] != "ready":
        log_event(signal, "rejected", reason=evaluation.get("reason"))
        send_message(f"Trade blocked after approval: {evaluation.get('reason')}")
        return action, evaluation

    if not EXECUTION_ENABLED:
        log_event(signal, "approved", reason="execution_disabled")
        send_message("TradingView signal approved. Execution is disabled.")
        return action, {
            "status": "approved",
            "execution": "disabled",
            "signal": signal_to_dict(signal),
            "market_regime": evaluation.get("market_regime"),
            "regime_confidence": evaluation.get("regime_confidence"),
            "transition_alert": evaluation.get("transition_alert"),
            "transition_score": evaluation.get("transition_score"),
            "transition_type": evaluation.get("transition_type"),
            "arbitration": evaluation.get("arbitration"),
            "discipline": evaluation.get("discipline"),
            "capital_requested": evaluation.get("capital_requested"),
            "portfolio_advisory": evaluation.get("portfolio_advisory"),
        }

    send_message("Executing approved TradingView trade...")
    result = execute_signal(signal)
    send_message(f"Trade executed: {signal.side} {signal.qty} {signal.symbol}")
    return action, result


def _approval_worker() -> None:
    while True:
        try:
            handle_telegram_decision()
        except Exception as exc:
            print("[TRADINGVIEW APPROVAL WORKER ERROR]", exc)

        time.sleep(APPROVAL_POLL_SECONDS)


def start_approval_worker() -> None:
    global _approval_worker_started

    if not APPROVAL_ENABLED or not APPROVAL_WORKER_ENABLED:
        return

    with _approval_worker_lock:
        if _approval_worker_started:
            return

        thread = threading.Thread(target=_approval_worker, daemon=True)
        thread.start()
        _approval_worker_started = True


@app.route("/health", methods=["GET"])
def health():
    expire_pending_approvals()
    return jsonify(
        {
            "status": "ok",
            "service": "tradingview_bridge",
            "approval_enabled": APPROVAL_ENABLED,
            "execution_enabled": EXECUTION_ENABLED,
            "broker_mode": BROKER_MODE,
            "pending": len(PENDING_SIGNALS),
            "duplicate_cache": len(DUPLICATE_CACHE),
            "nonce_cache": len(NONCE_CACHE),
        }
    )


@app.route("/", methods=["GET"])
def root():
    expire_pending_approvals()
    rows = []

    for symbol, pending in PENDING_SIGNALS.items():
        signal = pending.signal
        expires_in = max(0, int(pending.expires_at - time.time()))
        rows.append(
            "<tr>"
            f"<td>{escape(symbol)}</td>"
            f"<td>{escape(signal.side)}</td>"
            f"<td>{escape(str(signal.qty))}</td>"
            f"<td>{escape(signal.source)}</td>"
            f"<td>{escape(signal.strategy)}</td>"
            f"<td>{expires_in}s</td>"
            "</tr>"
        )

    pending_rows = "".join(rows) or "<tr><td colspan='6'>No pending approvals</td></tr>"

    return f"""
    <!doctype html>
    <html>
      <head>
        <title>QE3 TradingView Bridge</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 32px; background: #f7f7f8; color: #1f2933; }}
          h1 {{ margin-bottom: 8px; }}
          .status {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; margin: 24px 0; }}
          .box {{ background: white; border: 1px solid #ddd; border-radius: 6px; padding: 14px; }}
          .label {{ color: #667085; font-size: 12px; text-transform: uppercase; }}
          .value {{ font-size: 20px; margin-top: 6px; }}
          table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #ddd; }}
          th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #eee; }}
        </style>
      </head>
      <body>
        <h1>QE3 TradingView Bridge</h1>
        <div>Webhook service is online.</div>
        <div class="status">
          <div class="box"><div class="label">Broker Mode</div><div class="value">{escape(BROKER_MODE)}</div></div>
          <div class="box"><div class="label">Approval</div><div class="value">{escape(str(APPROVAL_ENABLED))}</div></div>
          <div class="box"><div class="label">Pending</div><div class="value">{len(PENDING_SIGNALS)}</div></div>
          <div class="box"><div class="label">Execution</div><div class="value">{escape(str(EXECUTION_ENABLED))}</div></div>
        </div>
        <h2>Pending Approvals</h2>
        <table>
          <thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Source</th><th>Strategy</th><th>Expires</th></tr></thead>
          <tbody>{pending_rows}</tbody>
        </table>
      </body>
    </html>
    """


@app.route("/telegram/poll", methods=["POST"])
def telegram_poll():
    action, result = handle_telegram_decision()
    return jsonify({"status": "ok", "action": action, "result": result})


@app.route("/tv-webhook", methods=["POST"])
@app.route("/tradingview-webhook", methods=["POST"])
def tv_webhook():
    expire_pending_approvals()
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        log_event(None, "rejected", reason="invalid_json")
        return jsonify({"status": "error", "msg": "invalid or empty JSON payload"}), 400

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

        evaluation = _evaluate_tradingview_signal(signal)
        if evaluation["status"] != "ready":
            log_event(signal, evaluation["status"], reason=evaluation.get("reason"))
            evaluation["signal_id"] = signal_id
            return jsonify(evaluation)

        if APPROVAL_ENABLED:
            response = queue_for_telegram_approval(signal)
            response["signal_id"] = signal_id
            response["execution_enabled"] = EXECUTION_ENABLED

        elif EXECUTION_ENABLED:
            response = execute_signal(signal)
            response["signal_id"] = signal_id

        else:
            response = {
                "status": "recorded",
                "signal_id": signal_id,
                "signal": signal_to_dict(signal),
                "execution_enabled": EXECUTION_ENABLED,
                "approval_enabled": APPROVAL_ENABLED,
                "regime": evaluation.get("market_regime"),
                "regime_confidence": evaluation.get("regime_confidence"),
                "transition_alert": evaluation.get("transition_alert"),
                "transition_score": evaluation.get("transition_score"),
                "transition_type": evaluation.get("transition_type"),
                "arbitration": evaluation.get("arbitration"),
                "discipline": evaluation.get("discipline"),
                "capital_requested": evaluation.get("capital_requested"),
                "portfolio_advisory": evaluation.get("portfolio_advisory"),
            }
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
