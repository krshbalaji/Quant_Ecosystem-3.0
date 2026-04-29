from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# -----------------------------
# Shared API key for control endpoints
# -----------------------------
API_KEY = os.getenv("CLOUD_API_KEY")


def authorize():
    incoming = request.headers.get("X-API-KEY")

    if incoming != API_KEY:
        return jsonify({
            "authorized": False,
            "error": "unauthorized"
        }), 401

    return None


# -----------------------------
# Shadow runtime state
# True = BLOCK signals
# False = allow paper dispatch
# -----------------------------
STATE = {
    "kill_switch": True,
    "paper_dispatch_enabled": True,
    "last_signal": None
}


@app.get("/")
def health():
    return {
        "status": "ok",
        "mode": os.getenv("EXECUTION_MODE", "D"),
        "paper_mode": os.getenv("PAPER_MODE", "true"),
        "live_broker_disabled": os.getenv("LIVE_BROKER_DISABLED", "true")
    }


@app.get("/status")
def status():
    return STATE


@app.post("/kill-switch")
def kill_switch():

    # --- AUTH CHECK ---
    auth = authorize()
    if auth:
        return auth

    payload = request.get_json(silent=True) or {}

    enabled = bool(payload.get("enabled", True))

    # True = emergency stop ON
    # False = signals allowed
    STATE["kill_switch"] = enabled

    return {
        "kill_switch": enabled,
        "message": "updated"
    }


@app.post("/signal")
def signal():

    # --- AUTH CHECK ---
    auth = authorize()
    if auth:
        return auth

    # --- HARD SAFETY GATE ---
    if STATE["kill_switch"] is True:
        return jsonify({
            "accepted": False,
            "reason": "kill_switch_active",
            "dispatch_mode": None
        }), 403

    payload = request.get_json(silent=True) or {}

    signal_data = {
        "symbol": payload.get("symbol"),
        "side": payload.get("side"),
        "qty": payload.get("qty"),
        "execution_mode": os.getenv("EXECUTION_MODE", "D"),
        "paper_only": True
    }

    STATE["last_signal"] = signal_data

    # Future hook:
    # OpportunityRanker -> RiskEngine -> ExecutionPolicyManager

    return {
        "accepted": True,
        "dispatch_mode": "paper_shadow",
        "signal": signal_data
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)