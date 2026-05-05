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
from telegram_control import send_message, ask_trade_details

# ------------------ CONFIG ------------------
SCAN_INTERVAL = 15
MIN_STRENGTH = 0.4
COOLDOWN_SECONDS = 900
MAX_TRADES_PER_DAY = 3

recent_trades = {}
trade_count = 0

logger = get_logger(__name__)

brain = StrategyBrain(IndicatorAdapter())
state = TradeState(cooldown=120)


# ------------------ ENTRY SCORE ------------------
def entry_score(md):

    if isinstance(md, dict):
        return 2  # allow dict-based data (basic pass)

    score = 0

    if md["Close"].iloc[-1] > md["Close"].rolling(20).mean().iloc[-1]:
        score += 1

    if md["Close"].iloc[-1] > md["High"].rolling(10).max().iloc[-2]:
        score += 2

    if md["Volume"].iloc[-1] > md["Volume"].rolling(20).mean().iloc[-1]:
        score += 1

    return score

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
# ------------------ MAIN LOOP ------------------
if __name__ == "__main__":

    logger.info("🧠 Precision Trading System Started...")

    while True:
        try:
            now = time.time()

            # Clean cooldown
            recent_trades = {
                s: t for s, t in recent_trades.items()
                if now - t < COOLDOWN_SECONDS
            }

            regime = get_market_regime()
            print(f"[MARKET REGIME] {regime}")

            symbols = get_dynamic_universe()

            candidates = []

            # ---- SCAN ----
            for symbol in symbols:

                md = provider.get_data(symbol)   # ✅ FIRST define md

                if md is None:
                    continue

                # ---- HANDLE BOTH TYPES ----
                if isinstance(md, dict):
                    if not md.get("price"):
                        continue
                else:
                    if md.empty:
                        continue

                # ---- NOW normalize ----
                data = normalize_md(md)

                entry = data["price"]
                atr = data["atr"]

                decision = brain.decide(symbol)
                if not decision:
                    continue

                score = score_signal(decision, md)
                strength = decision["strength"]

                print(f"[DEBUG] {symbol} score={score} strength={strength}")

                if strength < MIN_STRENGTH:
                    continue

                es = entry_score(md)

                if es < 2:
                    continue

                # Tier system
                if score >= 100 and strength >= 1.2:
                    tier = "A"
                elif score >= 80 and strength >= 1.0:
                    tier = "B"
                else:
                    continue

                candidates.append({
                    "symbol": symbol,
                    "decision": decision,
                    "score": score,
                    "tier": tier,
                    "md": md
                })

            if not candidates:
                print("[NO TRADE]")
                time.sleep(SCAN_INTERVAL)
                continue

            # ---- SELECT BEST ----
            candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
            best = candidates[0]

            symbol = best["symbol"]
            decision = best["decision"]
            md = best["md"]

            print(f"[SELECTED] {symbol} tier={best['tier']}")

            # ---- ENTRY PRICE ----
            if isinstance(md, dict):
                entry = md.get("price")
            else:
                entry = md["Close"].iloc[-1]

            # ---- ATR DYNAMIC SL/TP ----
            if isinstance(md, dict):
                atr = md.get("atr", 0.5)  # fallback
            else:
                atr = md["Close"].rolling(14).std().iloc[-1]
                
            if decision["side"] == "BUY":
                sl = entry - (1.2 * atr)
                tp = entry + (2.5 * atr)
            else:
                sl = entry + (1.2 * atr)
                tp = entry - (2.5 * atr)

            # ---- CAPITAL ----
            ok, reason = can_take_trade()
            if not ok:
                print(f"[CAPITAL BLOCK] {reason}")
                continue

            qty, _ = compute_qty(entry, sl, lot_size=1, max_lot_cap=4)

            if not qty or qty <= 0:
                continue

            if symbol in recent_trades:
                print(f"[SKIP] {symbol} in cooldown")
                continue
            
            active_positions = set()

            if symbol in active_positions:
                print(f"[SKIP] {symbol} already active")
                continue   

            # ---- TELEGRAM ----
            result = ask_trade_details(symbol, decision["side"], entry)

            if not result:
                continue

            qty, entry = result

            send_message("🟡 Executing Trade...")
            decision = ask_trade_details(symbol, side, entry)

            # ---- EXECUTE ----
            success = execute_signal(symbol, decision["side"], qty, entry)

            if success:
                send_message("✅ Trade Executed")
                recent_trades[symbol] = time.time()
                trade_count += 1
            else:
                send_message("⚠ Trade Rejected")

            if entry is None:
                order_type = "MARKET"
            else:
                order_type = "LIMIT"
                
            recent_trades[symbol] = time.time()
            
            active_positions.add(symbol)

        except Exception as e:
            logger.error(f"[ERROR] {e}")

        time.sleep(SCAN_INTERVAL)