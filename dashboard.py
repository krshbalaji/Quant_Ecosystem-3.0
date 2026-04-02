import streamlit as st
import yfinance as yf
import time
from auto_adaptive_engine import regime, participation, decision_engine, time_phase
from alerts import play_alert, send_telegram
from strategy_memory import best_strategy
st.set_page_config(layout="centered")
st.markdown("<meta name='viewport' content='width=device-width, initial-scale=1.0'>", unsafe_allow_html=True)
from multi_asset_scanner import scan_market
from execution_engine import execute_trade

if st.button("🚀 Execute Trade"):

    execute_trade(strategy, capital, SYMBOL)
    
SYMBOL = scan_market() or "^NSEBANK"

st.set_page_config(page_title="Desk Brain", layout="wide")

st.title("🧠 INSTITUTIONAL DESK DASHBOARD")

from quant_ecosystem.research.performance.live_pnl_engine import LivePnLEngine

pnl = LivePnLEngine().summary()

st.metric("Total PnL", pnl["total_pnl"])



placeholder = st.empty()

while True:

    df = yf.download(SYMBOL, period="1d", interval="5m", progress=False)

    if df is None or len(df) < 50:
        st.error("No market data")
        time.sleep(5)
        continue

    reg = regime(df)
    part = participation(df)
    phase = time_phase()

    st.write("FILE PATH:", FILE)
    
    from evolution_engine import best_strategy, worst_strategy

    strategy, capital, note = decision_engine(reg, part, phase)

    best = best_strategy()

    if best:
        strategy = best

    worst = worst_strategy()

    if strategy == worst:
        capital = capital * 0.5  # reduce risk on weak strategy
        
    # 🧠 STRATEGY EVOLUTION (V17)
    best = best_strategy(reg)

    if best:
        strategy = best
        
    with placeholder.container():

        col1, col2, col3 = st.columns(3)

        col1.metric("📊 Regime", reg)
        col2.metric("📈 Participation", round(part,2))
        col3.metric("🕒 Phase", phase)

        st.divider()

        col4, col5 = st.columns(2)

        col4.metric("🎯 Strategy", strategy)
        col5.metric("💰 Capital %", capital)

        st.divider()

        if capital > 0:
            st.success(f"✅ TRADE ACTIVE → {note}")
        else:
            st.error(f"❌ NO TRADE → {note}")

    time.sleep(5)

    registry = router.strategy_registry

    all_strategies = registry.get_all()

    auto_strategies = [
        s for s in all_strategies.values()
        if s.family == "auto_generated"
    ]

    if auto_strategies:
        strategy = auto_strategies[-1].name

    from strategy_memory import best_strategy

    best = best_strategy(reg)

    if best:
        strategy = best

    from ai_optimizer import suggest_strategy

    ai_choice = suggest_strategy(reg)

    if ai_choice:
        strategy = ai_choice    

    # 🔔 ALERT TRIGGER
last_signal = None
current_signal = "TRADE" if capital > 0 else "NO_TRADE"

if current_signal != last_signal:

    if current_signal == "TRADE":
        play_alert("TRADE")
        send_telegram(f"TRADE: {strategy} | Capital: {capital}% | Regime: {reg}")
    else:
        play_alert("NO_TRADE")

    last_signal = current_signal
    