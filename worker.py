import time
import json
import hashlib
from datetime import datetime, UTC

from config import Config
from infra.http_client import HttpClient
from infra.execution_router import route_execution
from infra.logger import get_logger
from quant_ecosystem.broker.paper_broker import PaperBroker
from quant_ecosystem.broker.broker_router import BrokerRouter
from indicator_adapter import IndicatorAdapter
from position_engine import add_position, remove_position, get_positions
from risk_engine import check_risk
from position_sizer import calculate_qty
from portfolio_brain import PortfolioBrain

logger = get_logger(__name__)
client = HttpClient()
portfolio = PortfolioBrain(capital=100000)
SEEN_FILE = "seen_ids.json"

broker = BrokerRouter(PaperBroker())
indicators = IndicatorAdapter()

MAX_LOSS = -2000


def sig_id(sig):
    raw = f"{sig.get('symbol')}|{sig.get('side')}"
    return hashlib.sha1(raw.encode()).hexdigest()

def load_json(path, default):
    try:
        return json.load(open(path))
    except:
        return default


def save_json(path, obj):
    json.dump(obj, open(path, "w"), indent=2)


def check_exit():
    positions = get_positions()

    for sym, pos in positions.items():
        if "side" not in pos:
            pos["side"] = "BUY"  # assume legacy long
        
        qty = pos["qty"]

        live = indicators.get_price(sym)

        side = pos.get("side", "BUY")  # fallback safety

        if side == "BUY":
            if live <= pos["stop_loss"] or live >= pos["take_profit"]:
                broker.place_order(sym, "SELL", qty)
                remove_position(sym)

        elif side == "SELL":
            if live >= pos["stop_loss"] or live <= pos["take_profit"]:
                broker.place_order(sym, "BUY", qty)
                remove_position(sym)
           
seen = set(load_json(SEEN_FILE, []))

logger.info("🚀 Worker connected to Quant Ecosystem...")

while True:
    try:
        # 🔴 Global PnL check
        positions = get_positions()
        pnl = 0

        for sym, pos in positions.items():
            live = indicators.get_price(sym)
            pnl += (live - pos["entry_price"]) * pos["qty"]

        if pnl < MAX_LOSS:
            logger.warning("🚨 Global loss hit")
            kill_result = client.send_post("/kill-switch", {"enabled": True})
            if not kill_result.get("success"):
                logger.warning("Kill switch request failed: %s", kill_result.get("error"))
            time.sleep(5)
            continue

        # 🔴 Exit
        check_exit()

        # 🔽 Get signal
        status_result = client.send_get("/status", timeout=10)

        if not status_result.get("success"):
            logger.warning("Failed to fetch status: %s", status_result.get("error"))
            time.sleep(2)
            continue

        data = status_result.get("data") or {}
        sig = data.get("last_signal")

        if not sig or not sig.get("symbol"):
            time.sleep(2)
            continue

        sid = sig_id(sig)

        if sid in seen:
            time.sleep(2)
            continue

        # ✅ mark immediately (IMPORTANT)
        
        sym = sig["symbol"]

        

        # 🔴 Risk check
        ok, reason = check_risk(sig)

        if not ok:
            print("RISK BLOCKED:", reason)
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

                # === GET MARKET DATA ===
        side = sig.get("side", "BUY")

        price = indicators.get_price(sym)
        atr = indicators.get_atr(sym)

        if price is None or atr is None:
            continue

        # === BUILD SL / TP ===
        if side == "BUY":
            stop_loss = price - atr * 1.5
            take_profit = price + atr * 3
        else:
            stop_loss = price + atr * 1.5
            take_profit = price - atr * 3

        # === PORTFOLIO CHECK ===
        if not portfolio.can_take_trade(positions, sym):
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

        # === POSITION SIZE ===
        qty = portfolio.calculate_position_size(price, stop_loss)

        strength = sig.get("strength", 1)
        qty = int(qty * strength)

        if qty < 1:
            qty = 1

        # 🔴 Skip if already holding
        positions = get_positions()
        if sym in positions:
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

        # === EXECUTION ===
        logger.info("🧪 PAPER ORDER: %s %s x%s", side, sym, qty)

        order = {
            "symbol": sym,
            "qty": qty,
            "side": side,
            "price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ts": datetime.now(UTC).isoformat(),
        }

        logger.info("ENTRY: %s", order)

        execution_result = route_execution(order)
        logger.info("Execution router response: %s", execution_result)

        if execution_result.get("mode") == "local":
            broker.place_order(sym, side, qty)
            add_position(order)
        elif execution_result.get("success"):
            add_position(order)
        else:
            raise RuntimeError(execution_result.get("error") or "Cloud execution failed")

        seen.add(sid)
        save_json(SEEN_FILE, list(seen))
        
    except Exception as e:
        logger.error("ERROR: %s", str(e))
        if Config.LOCAL_FALLBACK_ENABLED and all(name in locals() for name in ("sym", "side", "qty", "order", "sid")):
            try:
                logger.info("Falling back to local broker execution")
                broker.place_order(sym, side, qty)
                add_position(order)
                seen.add(sid)
                save_json(SEEN_FILE, list(seen))
            except Exception as local_exc:
                logger.error("Local fallback failed: %s", str(local_exc))
                raise
        elif not Config.LOCAL_FALLBACK_ENABLED:
            raise

    time.sleep(2)