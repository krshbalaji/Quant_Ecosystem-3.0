from flask import Flask, request, jsonify
import os
import json
import time

app = Flask(__name__)

# -------- CONFIG --------
API_KEY = os.getenv("CLOUD_API_KEY", "")

STATE = {
    "kill_switch": True,
    "last_signal": None
}

LAST_TS = {}
COOLDOWN_SEC = 5


# -------- AUTH --------
def authorized(req):
    return req.headers.get("X-API-KEY") == API_KEY


# -------- HEALTH --------
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


# -------- KILL SWITCH --------
@app.post("/kill-switch")
def kill_switch():
    if not authorized(request):
        return {"error": "unauthorized"}, 401

    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled", True))

    STATE["kill_switch"] = enabled

    return {
        "kill_switch": enabled,
        "message": "updated"
    }


# -------- SIGNAL --------
@app.post("/signal")
def signal():
    if not authorized(request):
        return {"error": "unauthorized"}, 401

    if STATE["kill_switch"]:
        return jsonify({
            "accepted": False,
            "reason": "Global kill switch active"
        }), 403

    payload = request.get_json(silent=True) or {}

    symbol = payload.get("symbol")
    side = payload.get("side")
    qty = payload.get("qty")

    if not symbol or not side or not qty:
        return {"error": "invalid signal"}, 400

    if side not in ["BUY", "SELL"]:
        return {"error": "invalid side"}, 400

    if int(qty) <= 0:
        return {"error": "invalid qty"}, 400

    now = time.time()

    # cooldown protection
    if symbol in LAST_TS and (now - LAST_TS[symbol]) < COOLDOWN_SEC:
        return {"accepted": False, "reason": "cooldown"}, 429

    LAST_TS[symbol] = now

    signal_data = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "execution_mode": os.getenv("EXECUTION_MODE", "D"),
        "paper_only": True
    }

    STATE["last_signal"] = signal_data

    # persist (important for reliability)
    with open("/tmp/last_signal.json", "w") as f:
        json.dump(signal_data, f)

    return {
        "accepted": True,
        "dispatch_mode": "paper_shadow",
        "signal": signal_data
    }


# -------- LATEST SIGNAL (for worker reliability) --------
@app.get("/latest-signal")
def latest_signal():
    try:
        return json.load(open("/tmp/last_signal.json"))
    except:
        return {}


# -------- RUN --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)