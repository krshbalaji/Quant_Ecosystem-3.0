from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Runtime state
STATE = {
    "kill_switch": True,   # default SAFE = ON
    "last_signal": None
}

API_KEY = os.getenv("CLOUD_API_KEY", "")

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

    # HARD SAFETY
    if STATE["kill_switch"]:
        return jsonify({
            "accepted": False,
            "reason": "Global kill switch active"
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

    return {
        "accepted": True,
        "dispatch_mode": "paper_shadow",
        "signal": signal_data
    }


# -------- RUN --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)