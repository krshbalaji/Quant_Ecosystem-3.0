import time
from infra.logger import get_logger

from strategy_brain import StrategyBrain
from trade_state import TradeState
from ai_engine import score_signal
from market_data_provider import provider
from indicator_adapter import IndicatorAdapter

from capital_allocator import can_take_trade, compute_qty
from precision_executor import execute_signal
from market_regime_intelligence import get_market_regime
from universe import get_dynamic_universe

# ✅ FIXED IMPORT
from telegram_control import send_message, start_trade_panel, process_callbacks

# ---------------- CONFIG ----------------
SCAN_INTERVAL = 30
MIN_STRENGTH = 0.4
COOLDOWN_SECONDS = 900
active_trade = None

recent_trades = {}
asked_signals = set()

logger = get_logger(__name__)

brain = StrategyBrain(IndicatorAdapter())
state = TradeState(cooldown=120)

# ---------------- PRICE ----------------
def get_price(md):
    try:
        if hasattr(md, "empty") and not md.empty:
            return float(md["Close"].iloc[-1])

        if isinstance(md, dict):
            return float(md.get("price"))

    except:
        return None

    return None

# ---------------- NORMALIZE ----------------
def normalize_md(md):

    if isinstance(md, dict):
        return {
            "price": md.get("price"),
            "atr": md.get("atr", 0.5)
        }

    return {
        "price": md["Close"].iloc[-1],
        "atr": md["Close"].rolling(14).std().iloc[-1],
        "df": md
    }

# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":

    logger.info("🧠 Precision Trading System Started...")

    while True:
        try:
            now = time.time()

            # cooldown clean
            recent_trades = {
                s: t for s, t in recent_trades.items()
                if now - t < COOLDOWN_SECONDS
            }

            regime = get_market_regime()
            print(f"[MARKET REGIME] {regime}")

            symbols = get_dynamic_universe()

            best = None
            best_score = 0

            # 🔁 Always listen for user actions
            action, data = process_callbacks()

            if action:
                print(f"[USER ACTION] {action} {data}")


            if action == "EXECUTE":
                qty = data.get("qty", 1)
                price = data.get("price", "MARKET")

                send_message("🟡 Executing Trade...")
                success = execute_signal(symbol, side, qty, price)

                if success:
                    send_message("✅ Trade Executed")
                    recent_trades[symbol] = time.time()

            elif action == "CANCEL":
                send_message("❌ Trade Cancelled")
                    
                
            # -------- SCAN --------
            for symbol in symbols:

                md = provider.get_data(symbol)

                if md is None:
                    continue

                if hasattr(md, "empty") and md.empty:
                    continue

                price = get_price(md)
                if price is None:
                    continue

                data = normalize_md(md)

                decision = brain.decide(symbol)
                if not decision:
                    continue

                score = score_signal(decision, md)
                strength = decision["strength"]

                print(f"[DEBUG] {symbol} score={score} strength={strength}")

                if strength < MIN_STRENGTH:
                    continue

                if score > best_score:
                    best_score = score
                    best = (symbol, decision, md)

            if not best:
                print("[NO TRADE]")
                time.sleep(SCAN_INTERVAL)
                continue

            symbol, decision, md = best
            strength = decision["strength"]

            print(f"[SELECTED] {symbol}")

            # -------- SIDE --------
            if regime == "BULL" and strength > 1:
                side = "BUY"
            elif regime == "BEAR" and strength > 1:
                side = "SELL"
            else:
                print("[REGIME BLOCK]")
                continue

            print(f"[DECISION] {symbol} {side}")

            entry = round(get_price(md), 2)

            if entry is None:
                continue

            # -------- CAPITAL --------
            ok, reason = can_take_trade()
            if not ok:
                print(f"[CAPITAL BLOCK] {reason}")
                continue
            
            if symbol in recent_trades:
                print(f"[COOLDOWN ACTIVE] {symbol}")
                continue

            if active_trade == symbol:
                print(f"[ACTIVE TRADE RUNNING] {symbol}")
                continue

            if symbol in asked_signals:
                continue


            # -------- DUPLICATE --------
            if symbol in recent_trades:
                continue

            if symbol in asked_signals:
                continue

            recent_trades[symbol] = time.time()
            asked_signals.add(symbol)

            # -------- TELEGRAM PANEL --------
            start_trade_panel(symbol, side, entry)

            print("[WAITING USER ACTION]")

            # -------- WAIT USER --------
            result = None

            action, data = process_callbacks()

            if action == "EXECUTE":
                qty = data["qty"]
                price = data["price"]

                send_message("🟡 Executing Trade...")
                success = execute_signal(symbol, side, qty, price)

                if success:
                    send_message("✅ Trade Executed")
                    recent_trades[symbol] = time.time()
                else:
                    send_message("⚠ Trade Failed")

            elif action == "CANCEL":
                send_message("❌ Trade Cancelled")

                if action == "EXECUTE":
                    result = data
                    break

                elif action == "CANCEL":
                    send_message("❌ Trade Cancelled")
                    break

                time.sleep(1)

            # -------- SKIP --------
            if result is None:
                continue

            if result and isinstance(result, dict):
                qty = result.get("qty", 1)
                price = result.get("price", "MARKET")
            else:
                send_message("❌ Trade Cancelled / No Input")
                continue

            asked_signals.add(symbol)

            send_message("🟡 Executing Trade...")

            success = execute_signal(symbol, side, qty, price)

            if success:
                send_message("✅ Trade Executed")
                recent_trades[symbol] = time.time()
            else:
                send_message("⚠ Trade Rejected")
            active_trade = symbol

            if now - recent_trades.get(symbol, 0) > 1800:
                active_trade = None


        except Exception as e:
            logger.error(f"[ERROR] {e}")

        time.sleep(SCAN_INTERVAL)