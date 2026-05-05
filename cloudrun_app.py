import os
from flask import Flask, request, jsonify
from google.cloud import firestore
from config import Config

from firestore_client import get_positions, update_position
from core.execution_engine_v2 import process_positions

app = Flask(__name__)

from execution_engine_v2 import process_positions

# ✅ FIXED
db = firestore.Client()

API_KEY = os.getenv("API_KEY") or os.getenv("CLOUD_API_KEY")


# ---- HEALTH ----
@app.route("/", methods=["GET"])
def health():
    return {
        "status": "alive",
        "mode": "cloud"
    }


# ---- GET PORTFOLIO ----
@app.route("/portfolio", methods=["GET"])
def portfolio():
    return jsonify({"positions": get_positions()})


# ---- CLEAR PORTFOLIO ----
@app.route("/portfolio/clear", methods=["DELETE"])
def clear_portfolio():
    try:
        incoming_key = request.headers.get("X-API-KEY")

        if incoming_key != API_KEY:
            return {"error": "unauthorized"}, 401

        docs = db.collection("portfolio").stream()

        for doc in docs:
            db.collection("portfolio").document(doc.id).delete()

        return {"status": "portfolio cleared"}

    except Exception as e:
        return {"error": str(e)}, 500


# ---- SIGNAL (USES CORE LOGIC) ----
@app.route("/signal", methods=["POST"])
def signal():
    try:
        incoming_key = request.headers.get("X-API-KEY")

        if incoming_key != API_KEY:
            return jsonify({"error": "unauthorized"}), 401

        data = request.json or {}

        # 🔥 NO DUPLICATE LOGIC
        result = process_positions()

        return jsonify({"status": "processed", "result": result})

    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/process", methods=["POST"])
def process():
    process_positions()
    return {"status": "processed"}
    
# ---- RUN ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🔥 Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port)