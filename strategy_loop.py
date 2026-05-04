import time
from infra.logger import get_logger
from config import Config

from strategy_brain import StrategyBrain
from portfolio_allocator_v3 import PortfolioAllocatorV3
from trade_state import TradeState
from ai_engine import score_signal
from market_data_provider import provider
from indicator_adapter import IndicatorAdapter

from entry_timing import confirm_entry
from risk_manager import compute_levels
from capital_allocator import can_take_trade, compute_qty, register_trade
from portfolio_intelligence import rank_candidates, diversify
from precision_executor import execute_signal
from market_regime_intelligence import get_market_regime
from universe import get_dynamic_universe
from exit_engine import check_exits

logger = get_logger(__name__)

brain = StrategyBrain(IndicatorAdapter())
allocator = PortfolioAllocatorV3()
state = TradeState(cooldown=120)

SCAN_INTERVAL = 15
MIN_AI_SCORE = 80
MIN_STRENGTH = 1.0

if __name__ == "__main__":

    logger.info("🧠 Intelligent Trading System Started...")

    while True:

        try:
            market_data = {}

            regime = get_market_regime()
            print(f"[MARKET REGIME] {regime}")

            symbols = get_dynamic_universe(volatility_mode=(regime == "VOLATILE"))

            # ---- fetch data ----
            for symbol in symbols:
                market_data[symbol] = provider.get_data(symbol)

            check_exits(market_data)

            candidates = []

            for symbol in symbols:

                md = market_data.get(symbol)
                if not md:
                    continue

                if not state.can_trade(symbol):
                    continue

                decision = brain.decide(symbol)
                if not decision:
                    continue

                # ---- regime filter ----
                if regime == "BULL" and decision["side"] == "SELL":
                    continue
                if regime == "BEAR" and decision["side"] == "BUY":
                    continue

                # ---- entry timing ----
                valid, reason = confirm_entry(md, decision)
                if not valid:
                    continue

                score = score_signal(decision, md)

                if score < MIN_AI_SCORE:
                    continue

                if decision["strength"] < MIN_STRENGTH:
                    continue

                candidates.append({
                    "symbol": symbol,
                    "decision": decision,
                    "score": score
                })

            if not candidates:
                print("[NO TRADE]")
                time.sleep(SCAN_INTERVAL)
                continue

            ranked = rank_candidates(candidates)
            selected = diversify(ranked)

            print(f"[SELECTED] {[x['symbol'] for x in selected]}")

            for item in selected:

                symbol = item["symbol"]
                decision = item["decision"]
                md = market_data[symbol]

                entry, sl, tp = compute_levels(md, decision["side"])

                ok, reason = can_take_trade()
                if not ok:
                    print(f"[CAPITAL BLOCK] {reason}")
                    continue

                qty, msg = compute_qty(entry, sl, lot_size=1, max_lot_cap=4)
                if qty == 0:
                    continue

                alloc = {
                    "symbol": symbol,
                    "side": decision["side"],
                    "qty": qty,
                    "strength": decision["strength"]
                }

                execute_signal(alloc, entry)

                register_trade(sl, entry, qty)

        except Exception as e:
            logger.error(f"[ERROR] {e}")

        time.sleep(SCAN_INTERVAL)