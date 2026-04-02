import json
import os
from datetime import datetime
from pathlib import Path
from urllib import error, request

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from quant_ecosystem.operating.core.config_loader import Config
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # noqa: BLE001
    st_autorefresh = None


st.set_page_config(
    page_title="Quant Ecosystem Dashboard",
    page_icon="Q",
    layout="wide",
)


INITIAL_CAPITAL = 100000.0
PLOTLY_TEMPLATE = "plotly_dark"
DEFAULT_COCKPIT_URL = "http://127.0.0.1:8091"
CARD_BG = "#1E222A"
PAGE_BG = "#0E1117"
PROFIT = "#00FFAA"
LOSS = "#FF4B4B"
WARN = "#F6C445"
CFG = Config()


def resolve_trade_file():
    app_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(app_dir, "..", ".."))
    candidate_files = [
        os.path.join(project_root, "storage", "trade_journal.json"),
        os.path.join(project_root, "trade_journal.json"),
        os.path.join(project_root, "trade_journal1.json"),
        os.path.join(os.path.abspath(os.path.join(app_dir, "..")), "trade_journal.json"),
    ]
    selected = next((path for path in candidate_files if os.path.exists(path)), candidate_files[0])
    return selected, candidate_files, project_root


def runtime_paths(project_root):
    runtime_dir = Path(project_root) / "quant_ecosystem" / "reporting" / "output" / "runtime"
    eod_dir = Path(project_root) / "quant_ecosystem" / "reporting" / "output"
    return runtime_dir, eod_dir


@st.cache_data(ttl=5, show_spinner=False)
def load_latest_runtime_snapshot(runtime_dir):
    files = sorted(Path(runtime_dir).glob("cycle_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {}
    with open(files[0], "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["_source_file"] = str(files[0])
    return payload


@st.cache_data(ttl=10, show_spinner=False)
def load_latest_eod_summary(eod_dir):
    files = sorted(Path(eod_dir).glob("eod_summary_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {}
    with open(files[0], "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["_source_file"] = str(files[0])
    return payload


@st.cache_data(ttl=2, show_spinner=False)
def load_recent_logs(project_root, limit=20):
    log_file = Path(project_root) / "storage" / "logs" / "system.log"
    if not log_file.exists():
        return []
    with open(log_file, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    return [line.rstrip() for line in lines[-int(limit):]]


@st.cache_data(ttl=2, show_spinner=False)
def load_performance_log(project_root):
    path = Path(project_root) / "storage" / "performance_log.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def require_dashboard_login():
    if not bool(getattr(CFG, "enable_dashboard_auth", False)):
        return
    if st.session_state.get("dashboard_auth_ok"):
        return
    st.title("Quant Ecosystem Access")
    with st.form("dashboard_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        if username == getattr(CFG, "dashboard_admin_username", "") and password == getattr(CFG, "dashboard_admin_password", ""):
            st.session_state["dashboard_auth_ok"] = True
            st.session_state["dashboard_role"] = "admin"
            st.rerun()
        if username == getattr(CFG, "dashboard_viewer_username", "") and password == getattr(CFG, "dashboard_viewer_password", ""):
            st.session_state["dashboard_auth_ok"] = True
            st.session_state["dashboard_role"] = "viewer"
            st.rerun()
        st.error("Invalid credentials.")
    st.stop()


def current_dashboard_role():
    if not bool(getattr(CFG, "enable_dashboard_auth", False)):
        return "admin"
    return str(st.session_state.get("dashboard_role", "viewer")).lower()


@st.cache_data(ttl=2, show_spinner=False)
def fetch_cockpit_state(base_url, token):
    normalized = str(base_url or "").rstrip("/")
    if not normalized:
        return {"online": False, "error": "missing_cockpit_url"}

    endpoints = [
        ("system", "/system/status"),
        ("strategies", "/strategies"),
        ("portfolio", "/portfolio"),
    ]
    out = {"online": True, "base_url": normalized}
    headers = {}
    if token:
        headers["x-operator-token"] = token

    for key, suffix in endpoints:
        req = request.Request(normalized + suffix, headers=headers, method="GET")
        with request.urlopen(req, timeout=2.5) as resp:
            out[key] = json.loads(resp.read().decode("utf-8"))
    return out


def send_cockpit_command(base_url, token, command, payload=None):
    normalized = str(base_url or "").rstrip("/")
    body = json.dumps({"command": command, "payload": payload or {}}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["x-operator-token"] = token
    req = request.Request(normalized + "/command", data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=4.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def safe_fetch_cockpit_state(base_url, token):
    try:
        return fetch_cockpit_state(base_url, token)
    except Exception as exc:
        return {"online": False, "error": str(exc), "base_url": str(base_url or "").rstrip("/")}


def safe_send_cockpit_command(base_url, token, command, payload=None):
    try:
        result = send_cockpit_command(base_url, token, command, payload)
        return {"ok": True, "response": result}
    except error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@st.cache_data(ttl=5, show_spinner=False)
def load_trade_data(file_path):
    with open(file_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, list):
        raise ValueError("Trade journal must contain a JSON list.")

    df = pd.DataFrame(raw)
    if df.empty:
        return df

    expected_columns = ["time", "symbol", "strategy", "side", "qty", "pnl", "regime", "entry", "exit"]
    for column in expected_columns:
        if column not in df.columns:
            df[column] = None

    df["symbol"] = df["symbol"].fillna("UNKNOWN").astype(str)
    df["strategy"] = df["strategy"].fillna("UNSPECIFIED").astype(str)
    df["side"] = df["side"].fillna("NA").astype(str)
    df["regime"] = df["regime"].fillna("NA").astype(str)
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0.0)
    df["entry"] = pd.to_numeric(df["entry"], errors="coerce")
    df["exit"] = pd.to_numeric(df["exit"], errors="coerce")
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    df["timestamp"] = pd.to_datetime(df["time"], errors="coerce")
    df["trade_number"] = range(1, len(df) + 1)
    df["trade_key"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["trade_key"] = df["trade_key"].fillna("Trade #" + df["trade_number"].astype(str))
    df["result"] = df["pnl"].apply(lambda value: "Win" if value > 0 else "Loss" if value < 0 else "Flat")
    df["cumulative_pnl"] = df["pnl"].cumsum()
    df["equity"] = INITIAL_CAPITAL + df["cumulative_pnl"]
    df["equity_peak"] = df["equity"].cummax()
    df["drawdown"] = df["equity"] - df["equity_peak"]
    df["drawdown_pct"] = (df["drawdown"] / df["equity_peak"].replace(0, pd.NA)).fillna(0.0) * 100

    if df["timestamp"].notna().any():
        df["session_day"] = df["timestamp"].dt.date.astype(str)
    else:
        df["session_day"] = "Unknown"

    return df


def compute_summary(df):
    if df.empty:
        return {
            "total_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_trade": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "max_drawdown": 0.0,
            "current_streak": 0,
            "streak_label": "Flat",
            "active_symbols": 0,
            "active_strategies": 0,
        }

    wins = df[df["pnl"] > 0]["pnl"]
    losses = df[df["pnl"] < 0]["pnl"]
    total_trades = len(df)
    total_pnl = float(df["pnl"].sum())
    gross_profit = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses.sum())) if not losses.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    win_rate = float((df["pnl"] > 0).mean() * 100) if total_trades else 0.0

    streak = 0
    streak_label = "Flat"
    for pnl in reversed(df["pnl"].tolist()):
        if pnl > 0:
            if streak_label in ("Flat", "Winning"):
                streak += 1
                streak_label = "Winning"
            else:
                break
        elif pnl < 0:
            if streak_label in ("Flat", "Losing"):
                streak += 1
                streak_label = "Losing"
            else:
                break
        else:
            break

    return {
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade": float(df["pnl"].mean()),
        "best_trade": float(df["pnl"].max()),
        "worst_trade": float(df["pnl"].min()),
        "max_drawdown": float(df["drawdown"].min()),
        "current_streak": streak,
        "streak_label": streak_label,
        "active_symbols": int(df["symbol"].nunique()),
        "active_strategies": int(df["strategy"].nunique()),
    }


def render_header(file_path, summary, df):
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #0b0f14 0%, #0E1117 100%);
        }
        .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 1.5rem;
        }
        .hero {
            padding: 1.2rem 1.4rem;
            border: 1px solid rgba(120, 140, 160, 0.22);
            border-radius: 18px;
            background:
                radial-gradient(circle at top left, rgba(18, 123, 107, 0.28), transparent 34%),
                linear-gradient(135deg, rgba(12, 16, 22, 0.98), rgba(22, 28, 38, 0.96));
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 2.4rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
            letter-spacing: 0.02em;
        }
        .hero-subtitle {
            color: #97a6ba;
            font-size: 0.98rem;
        }
        .status-pill {
            display: inline-block;
            margin-top: 0.9rem;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: rgba(32, 182, 112, 0.14);
            border: 1px solid rgba(32, 182, 112, 0.45);
            color: #7ee2ab;
            font-size: 0.92rem;
        }
        .metric-card {
            background: #1E222A;
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            min-height: 118px;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.18);
        }
        .metric-label {
            color: #8ea1b8;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .metric-value {
            color: #f3f6fb;
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 0.4rem;
        }
        .metric-note {
            color: #6f8196;
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }
        .log-panel {
            background: #131922;
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 16px;
            padding: 0.75rem 0.9rem;
            max-height: 360px;
            overflow-y: auto;
            font-family: Consolas, monospace;
            font-size: 0.84rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    last_update = "No timestamps"
    if not df.empty and df["timestamp"].notna().any():
        last_update = df["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">Quant Ecosystem Control Center</div>
            <div class="hero-subtitle">
                Production-style execution dashboard for trade analytics, performance monitoring, and operator review.
            </div>
            <div class="status-pill">Data source online | Last update: {last_update}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2])
    with left:
        st.caption(f"Trade journal: `{file_path}`")
    with right:
        st.caption(
            f"PnL {summary['total_pnl']:,.2f} | Trades {summary['total_trades']} | "
            f"Strategies {summary['active_strategies']} | Symbols {summary['active_symbols']}"
        )


def render_kpis(summary):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Net PnL", f"{summary['total_pnl']:,.2f}")
    col2.metric("Win Rate", f"{summary['win_rate']:.1f}%")
    col3.metric("Profit Factor", f"{summary['profit_factor']:.2f}")
    col4.metric("Avg Trade", f"{summary['avg_trade']:,.2f}")
    col5.metric("Best / Worst", f"{summary['best_trade']:,.2f} / {summary['worst_trade']:,.2f}")
    col6.metric("Max Drawdown", f"{summary['max_drawdown']:,.2f}")


def render_runtime_cards(runtime_snapshot):
    state = runtime_snapshot.get("state", {}) if runtime_snapshot else {}
    result = runtime_snapshot.get("result", {}) if runtime_snapshot else {}
    regime = result.get("regime") or state.get("regime") or "LOW_VOLATILITY"
    active_symbols = list(state.get("active_symbols", []) or [])
    equity = float(state.get("equity", INITIAL_CAPITAL) or INITIAL_CAPITAL)
    cash = float(state.get("cash_balance", equity) or equity)
    capital_usage = max(0.0, min(100.0, ((equity - cash) / max(equity, 1.0)) * 100.0))
    last_signal = result.get("status") or state.get("last_signal", {}).get("strategy_id") or "WAITING"
    cards = [
        ("Regime", regime, "Desk state"),
        ("Active Symbols", ", ".join(active_symbols[:3]) if active_symbols else "Watching", f"{len(active_symbols)} tracked"),
        ("Capital Usage %", f"{capital_usage:.1f}%", f"Equity {equity:,.0f}"),
        ("Last Signal", last_signal, result.get("symbol", "No active symbol")),
    ]
    cols = st.columns(4)
    for col, (label, value, note) in zip(cols, cards):
        col.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def pnl_color(val):
    try:
        value = float(val)
    except Exception:  # noqa: BLE001
        return ""
    return f"color: {PROFIT}" if value > 0 else (f"color: {LOSS}" if value < 0 else f"color: {WARN}")


def render_equity_curve(df):
    chart_df = df.copy()
    chart_df["x_axis"] = chart_df["timestamp"]
    if chart_df["timestamp"].isna().all():
        chart_df["x_axis"] = chart_df["trade_number"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df["x_axis"],
            y=chart_df["equity"],
            mode="lines+markers",
            name="Equity",
            line=dict(color="#36cfc9", width=3),
            marker=dict(size=7),
            hovertemplate="Equity: %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=chart_df["x_axis"],
            y=chart_df["pnl"],
            name="Trade PnL",
            marker_color=["#1f9d55" if value >= 0 else "#d64545" for value in chart_df["pnl"]],
            opacity=0.45,
            yaxis="y2",
            hovertemplate="PnL: %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(title="Equity"),
        yaxis2=dict(title="Trade PnL", overlaying="y", side="right", showgrid=False),
        xaxis_title="Timestamp" if chart_df["timestamp"].notna().any() else "Trade Number",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_drawdown_curve(df):
    chart_df = df.copy()
    chart_df["x_axis"] = chart_df["timestamp"]
    if chart_df["timestamp"].isna().all():
        chart_df["x_axis"] = chart_df["trade_number"]

    fig = px.area(
        chart_df,
        x="x_axis",
        y="drawdown",
        template=PLOTLY_TEMPLATE,
        color_discrete_sequence=["#ff6b6b"],
    )
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Timestamp" if chart_df["timestamp"].notna().any() else "Trade Number",
        yaxis_title="Drawdown",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_group_charts(df):
    left, right = st.columns(2)

    strategy_df = (
        df.groupby("strategy", as_index=False)
        .agg(total_pnl=("pnl", "sum"), trades=("strategy", "size"))
        .sort_values("total_pnl", ascending=False)
    )
    symbol_df = (
        df.groupby("symbol", as_index=False)
        .agg(total_pnl=("pnl", "sum"), trades=("symbol", "size"))
        .sort_values("trades", ascending=False)
    )

    with left:
        strategy_fig = px.bar(
            strategy_df,
            x="strategy",
            y="total_pnl",
            color="total_pnl",
            color_continuous_scale=["#d64545", "#4f81ff", "#1fdb8a"],
            template=PLOTLY_TEMPLATE,
            text="trades",
            title="Strategy Contribution",
        )
        strategy_fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), coloraxis_showscale=False)
        strategy_fig.update_traces(texttemplate="%{text} trades", textposition="outside")
        st.plotly_chart(strategy_fig, use_container_width=True)

    with right:
        symbol_fig = px.pie(
            symbol_df,
            names="symbol",
            values="trades",
            color_discrete_sequence=px.colors.sequential.Tealgrn,
            hole=0.58,
            template=PLOTLY_TEMPLATE,
            title="Symbol Exposure Mix",
        )
        symbol_fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(symbol_fig, use_container_width=True)


def render_time_analysis(df):
    if df["timestamp"].notna().any():
        daily_df = (
            df.groupby("session_day", as_index=False)
            .agg(daily_pnl=("pnl", "sum"), trades=("trade_number", "size"))
            .sort_values("session_day")
        )
        fig = px.bar(
            daily_df,
            x="session_day",
            y="daily_pnl",
            color="daily_pnl",
            color_continuous_scale=["#d64545", "#3c78d8", "#1fdb8a"],
            template=PLOTLY_TEMPLATE,
            text="trades",
            title="Daily PnL Distribution",
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10), coloraxis_showscale=False)
        fig.update_traces(texttemplate="%{text} trades", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        sequence_fig = px.bar(
            df,
            x="trade_number",
            y="pnl",
            color="result",
            template=PLOTLY_TEMPLATE,
            color_discrete_map={"Win": "#1fdb8a", "Loss": "#d64545", "Flat": "#8b949e"},
            title="Trade-by-Trade Outcome Sequence",
        )
        sequence_fig.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(sequence_fig, use_container_width=True)


def render_insights(df, summary):
    best_strategy_df = df.groupby("strategy")["pnl"].sum().sort_values(ascending=False)
    weakest_symbol_df = df.groupby("symbol")["pnl"].sum().sort_values()
    latest_trade = df.iloc[-1].to_dict()

    insight_rows = [
        ("Best strategy", best_strategy_df.index[0], f"{best_strategy_df.iloc[0]:,.2f} PnL"),
        ("Weakest symbol", weakest_symbol_df.index[0], f"{weakest_symbol_df.iloc[0]:,.2f} PnL"),
        (
            "Current streak",
            summary["streak_label"],
            f"{summary['current_streak']} trades",
        ),
        (
            "Last trade",
            latest_trade.get("symbol", "UNKNOWN"),
            f"{float(latest_trade.get('pnl', 0.0)):,.2f} PnL",
        ),
    ]

    insight_df = pd.DataFrame(insight_rows, columns=["Signal", "Entity", "Value"])
    st.dataframe(insight_df, use_container_width=True, hide_index=True)


def render_trade_blotter(df):
    blotter = df[
        ["trade_number", "timestamp", "symbol", "strategy", "side", "qty", "entry", "exit", "regime", "pnl", "equity"]
    ].copy()
    blotter["timestamp"] = blotter["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    blotter["timestamp"] = blotter["timestamp"].fillna("NA")
    blotter = blotter.rename(
        columns={
            "trade_number": "Trade #",
            "timestamp": "Timestamp",
            "symbol": "Symbol",
            "strategy": "Strategy",
            "side": "Side",
            "qty": "Qty",
            "entry": "Entry",
            "exit": "Exit",
            "regime": "Regime",
            "pnl": "PnL",
            "equity": "Equity",
        }
    )

    styled = blotter.sort_values("Trade #", ascending=False).style.map(pnl_color, subset=["PnL"]).map(pnl_color, subset=["Equity"])
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        column_config={
            "PnL": st.column_config.NumberColumn(format="%.2f"),
            "Equity": st.column_config.NumberColumn(format="%.2f"),
            "Entry": st.column_config.NumberColumn(format="%.2f"),
            "Exit": st.column_config.NumberColumn(format="%.2f"),
            "Qty": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def render_logs_panel(log_lines):
    if not log_lines:
        st.info("No system logs found yet.")
        return
    html_lines = []
    for line in log_lines:
        color = "#e7edf6"
        if "ERROR" in line:
            color = LOSS
        elif "WARNING" in line:
            color = WARN
        html_lines.append(f'<div style="color:{color}; margin-bottom:0.25rem;">{line}</div>')
    st.markdown(f'<div class="log-panel">{"".join(html_lines)}</div>', unsafe_allow_html=True)


def render_live_telemetry(runtime_snapshot):
    state = runtime_snapshot.get("state", {}) if runtime_snapshot else {}
    result = runtime_snapshot.get("result", {}) if runtime_snapshot else {}
    cols = st.columns(4)
    cols[0].metric("Cycle #", runtime_snapshot.get("cycle", 0) if runtime_snapshot else 0)
    cols[1].metric("Signals Generated", int(state.get("signal_count", 0) or 0))
    cols[2].metric("Trades Executed", int(state.get("trades_executed", 0) or 0))
    skipped = int(state.get("skipped_signals", 0) or 0)
    if result.get("status") == "SKIP":
        skipped = max(skipped, 1)
    cols[3].metric("Skipped Signals", skipped)


def render_system_thinking(runtime_snapshot):
    state = runtime_snapshot.get("state", {}) if runtime_snapshot else {}
    thinking = dict(state.get("system_thinking", {}) or {})
    if not thinking:
        st.info("System thinking will appear once intelligence context is populated.")
        return
    plan = dict(thinking.get("day_plan", {}) or {})
    rows = [
        ("Current Regime", thinking.get("regime", "UNKNOWN")),
        ("Market Bias", thinking.get("market_bias", "RANGE")),
        ("Risk Mode", thinking.get("risk_mode", "RISK_ON")),
        ("Event Type", thinking.get("event_type", "NONE")),
        ("Reason For Trades", thinking.get("last_reason", "Awaiting explanation")),
        ("Planned Symbols", ", ".join(list(plan.get("symbols", []) or [])[:4]) or "N/A"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Thinking", "Value"]), use_container_width=True, hide_index=True)


def render_strategy_performance(project_root):
    payload = load_performance_log(project_root)
    if not payload:
        st.info("No strategy performance log yet.")
        return
    rows = pd.DataFrame(payload.values()).sort_values(["total_pnl", "win_rate"], ascending=[False, False])
    st.dataframe(
        rows[["strategy_id", "trades", "win_rate", "avg_pnl", "avg_win", "avg_loss", "total_pnl"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "win_rate": st.column_config.NumberColumn("Win Rate", format="%.2f"),
            "avg_pnl": st.column_config.NumberColumn("Avg PnL", format="%.2f"),
            "avg_win": st.column_config.NumberColumn("Avg Win", format="%.2f"),
            "avg_loss": st.column_config.NumberColumn("Avg Loss", format="%.2f"),
            "total_pnl": st.column_config.NumberColumn("Total PnL", format="%.2f"),
        },
    )


def render_operator_panel(df, file_path, candidate_files):
    missing_time = int(df["timestamp"].isna().sum())
    missing_regime = int((df["regime"] == "NA").sum())
    system_rows = [
        ("Trade source", file_path),
        ("Candidate paths checked", " | ".join(candidate_files)),
        ("Trades loaded", str(len(df))),
        ("Missing timestamps", str(missing_time)),
        ("Missing regime tags", str(missing_regime)),
        ("Initial capital assumption", f"{INITIAL_CAPITAL:,.2f}"),
    ]
    system_df = pd.DataFrame(system_rows, columns=["Field", "Value"])
    st.dataframe(system_df, use_container_width=True, hide_index=True)


def render_runtime_monitor(runtime_snapshot, eod_summary):
    if not runtime_snapshot:
        st.info("No runtime snapshot files found yet.")
        return

    state = runtime_snapshot.get("state", {})
    result = runtime_snapshot.get("result", {})
    active_symbols = ", ".join(list(state.get("active_symbols", []) or [])[:6]) or "N/A"
    last_strategy = result.get("strategy_id") or state.get("last_strategy_id") or "N/A"
    last_signal = result.get("status", "N/A")
    top_cols = st.columns(5)
    top_cols[0].metric("Cycle", runtime_snapshot.get("cycle", 0))
    top_cols[1].metric("Runtime Status", str(result.get("status", "UNKNOWN")))
    top_cols[2].metric("Equity", f"{float(state.get('equity', 0.0)):,.2f}")
    top_cols[3].metric("Realized PnL", f"{float(state.get('realized_pnl', 0.0)):,.2f}")
    top_cols[4].metric("Drawdown %", f"{float(state.get('drawdown_pct', state.get('total_drawdown_pct', 0.0))):.2f}")

    st.caption(f"Runtime snapshot: `{runtime_snapshot.get('_source_file', 'N/A')}`")
    left, right = st.columns(2)
    with left:
        runtime_df = pd.DataFrame(
            [
                ("Timestamp", runtime_snapshot.get("timestamp", "N/A")),
                ("Account Source", state.get("account_source", "N/A")),
                ("Active Symbols", active_symbols),
                ("Last Strategy", last_strategy),
                ("Last Signal", last_signal),
                ("Open Positions", state.get("open_positions", 0)),
                ("Broker Positions", state.get("broker_positions_count", 0)),
                ("Broker Orders", state.get("broker_orders_count", 0)),
                ("Broker Trades", state.get("broker_trades_count", 0)),
                ("Cooldown", state.get("cooldown", 0)),
                ("Consecutive Losses", state.get("consecutive_losses", 0)),
            ],
            columns=["Field", "Value"],
        )
        st.dataframe(runtime_df, use_container_width=True, hide_index=True)
    with right:
        if eod_summary:
            portfolio = eod_summary.get("portfolio", {})
            eod_df = pd.DataFrame(
                [
                    ("Mode", eod_summary.get("mode", "N/A")),
                    ("Equity", portfolio.get("equity", 0)),
                    ("Peak Equity", portfolio.get("peak_equity", 0)),
                    ("Drawdown %", portfolio.get("drawdown_pct", 0)),
                    ("Cash Balance", portfolio.get("cash_balance", 0)),
                    ("Realized PnL", portfolio.get("realized_pnl", 0)),
                    ("Unrealized PnL", portfolio.get("unrealized_pnl", 0)),
                    ("Positions Count", (portfolio.get("broker") or {}).get("positions_count", 0)),
                ],
                columns=["Field", "Value"],
            )
            st.caption(f"EOD summary: `{eod_summary.get('_source_file', 'N/A')}`")
            st.dataframe(eod_df, use_container_width=True, hide_index=True)
        else:
            st.info("No EOD summary file found.")


def render_controller_tab(cockpit_state, base_url, token):
    st.subheader("Execution Control Plane")
    dashboard_role = current_dashboard_role()
    can_control = dashboard_role == "admin"
    if cockpit_state.get("online"):
        system = cockpit_state.get("system", {})
        portfolio = system.get("portfolio", {})
        market = system.get("market", {})
        engines = system.get("engines", {})
        cols = st.columns(5)
        cols[0].metric("Cockpit", "ONLINE")
        cols[1].metric("Regime", str(market.get("regime", "UNKNOWN")))
        cols[2].metric("Equity", f"{float(portfolio.get('equity', 0.0)):,.2f}")
        cols[3].metric("Open Positions", portfolio.get("open_positions", 0))
        cols[4].metric("Drawdown %", f"{float(portfolio.get('drawdown_pct', 0.0)):.2f}")
        st.caption(f"Connected to `{base_url}`")

        engine_rows = []
        for name, payload in engines.items():
            engine_rows.append(
                {
                    "Engine": name,
                    "Status": payload.get("status", "OFF"),
                    "Activity": payload.get("activity_level", 0),
                    "Last Seen": payload.get("last_event_ts", "N/A"),
                }
            )
        if engine_rows:
            st.dataframe(pd.DataFrame(engine_rows), use_container_width=True, hide_index=True)
    else:
        st.warning(
            "Cockpit API is offline, so the dashboard cannot issue live control commands yet. "
            "Monitoring from runtime snapshot files still works."
        )
        st.caption(f"Configured cockpit endpoint: `{base_url}`")
        if cockpit_state.get("error"):
            st.caption(f"Connection detail: `{cockpit_state['error']}`")

    action_cols = st.columns(4)
    if action_cols[0].button("Start Trading", use_container_width=True, disabled=not can_control):
        st.session_state["controller_result"] = safe_send_cockpit_command(base_url, token, "START_TRADING")
    if action_cols[1].button("Pause Trading", use_container_width=True, disabled=not can_control):
        st.session_state["controller_result"] = safe_send_cockpit_command(base_url, token, "PAUSE_TRADING")
    if action_cols[2].button("Emergency Stop", use_container_width=True, disabled=not can_control):
        st.session_state["controller_result"] = safe_send_cockpit_command(base_url, token, "EMERGENCY_STOP")
    if action_cols[3].button("Close All Positions", use_container_width=True, disabled=not can_control):
        st.session_state["controller_result"] = safe_send_cockpit_command(base_url, token, "CLOSE_ALL_POSITIONS")

    tuning_left, tuning_right = st.columns(2)
    with tuning_left:
        st.markdown("**Risk Controls**")
        risk_pct = st.number_input("Trade Risk %", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        max_dd = st.number_input("Max Drawdown %", min_value=1.0, max_value=50.0, value=20.0, step=0.5)
        if st.button("Apply Risk Settings", use_container_width=True, disabled=not can_control):
            risk_result = safe_send_cockpit_command(base_url, token, "SET_RISK_LEVEL", {"risk_pct": risk_pct})
            dd_result = safe_send_cockpit_command(base_url, token, "SET_MAX_DRAWDOWN", {"max_drawdown_pct": max_dd})
            st.session_state["controller_result"] = {"ok": risk_result.get("ok") and dd_result.get("ok"), "response": {"risk": risk_result, "drawdown": dd_result}}

    with tuning_right:
        st.markdown("**Execution Controls**")
        multiplier = st.number_input("Trade Size Multiplier", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        execution_mode = st.selectbox(
            "Execution Mode",
            ["LOW_SLIPPAGE_MODE", "BALANCED_MODE", "AGGRESSIVE_MODE"],
            index=0,
        )
        if st.button("Apply Execution Settings", use_container_width=True, disabled=not can_control):
            mul_result = safe_send_cockpit_command(base_url, token, "SET_TRADE_SIZE_MULTIPLIER", {"multiplier": multiplier})
            mode_result = safe_send_cockpit_command(base_url, token, "SET_EXECUTION_MODE", {"mode": execution_mode})
            st.session_state["controller_result"] = {"ok": mul_result.get("ok") and mode_result.get("ok"), "response": {"multiplier": mul_result, "mode": mode_result}}

    action_row = st.columns(2)
    if action_row[0].button("Reduce Exposure", use_container_width=True, disabled=not can_control):
        st.session_state["controller_result"] = safe_send_cockpit_command(base_url, token, "REDUCE_EXPOSURE")
    if action_row[1].button("Force Rebalance", use_container_width=True, disabled=not can_control):
        st.session_state["controller_result"] = safe_send_cockpit_command(base_url, token, "FORCE_REBALANCE")

    result = st.session_state.get("controller_result")
    if result:
        if result.get("ok"):
            st.success("Control command accepted.")
            response_rows = []
            for key, value in dict(result.get("response", {}) or {}).items():
                response_rows.append({"Field": key, "Value": value})
            if response_rows:
                st.dataframe(pd.DataFrame(response_rows), use_container_width=True, hide_index=True)
        else:
            st.error(f"Control command failed: {result.get('error', 'unknown_error')}")
    if not can_control:
        st.info("Viewer session: live control actions are disabled.")


def main():
    require_dashboard_login()
    file_path, candidate_files, project_root = resolve_trade_file()
    runtime_dir, eod_dir = runtime_paths(project_root)
    if st_autorefresh is not None:
        st_autorefresh(interval=3000, key="quant_dashboard_autorefresh")

    st.sidebar.title("Desk Controls")
    st.sidebar.caption("Local operator console for the quant ecosystem.")
    st.sidebar.caption(f"Session role: `{current_dashboard_role()}`")
    if st.sidebar.button("Refresh Data", use_container_width=True):
        load_trade_data.clear()
        load_latest_runtime_snapshot.clear()
        load_latest_eod_summary.clear()
        fetch_cockpit_state.clear()
        st.rerun()

    cockpit_url = st.sidebar.text_input("Cockpit API URL", value=DEFAULT_COCKPIT_URL)
    cockpit_token = st.sidebar.text_input("Operator Token", value="", type="password")
    st.sidebar.caption("When the cockpit server is live, this page becomes an active controller dashboard.")

    if not os.path.exists(file_path):
        st.error("Trade journal not found.")
        st.write(candidate_files)
        st.stop()

    try:
        df = load_trade_data(file_path)
    except Exception as exc:
        st.error(f"Failed to load trade journal: {exc}")
        st.stop()

    runtime_snapshot = load_latest_runtime_snapshot(runtime_dir)
    eod_summary = load_latest_eod_summary(eod_dir)
    recent_logs = load_recent_logs(project_root)
    cockpit_state = safe_fetch_cockpit_state(cockpit_url, cockpit_token)

    summary = compute_summary(df)
    render_header(file_path, summary, df)
    render_runtime_cards(runtime_snapshot)
    render_live_telemetry(runtime_snapshot)

    if df.empty:
        st.warning("Trade journal is empty. The dashboard is online, but there are no executed trades to analyze yet.")
        return

    render_kpis(summary)
    st.divider()

    overview_tab, analytics_tab, controller_tab, blotter_tab, ops_tab = st.tabs(
        ["Overview", "Analytics", "Controller", "Trade Blotter", "Ops Monitor"]
    )

    with overview_tab:
        left, right = st.columns([2, 1])
        with left:
            st.subheader("Equity Curve")
            render_equity_curve(df)
        with right:
            st.subheader("System Thinking")
            render_system_thinking(runtime_snapshot)
            st.subheader("Drawdown Profile")
            render_drawdown_curve(df)
            st.subheader("Desk Insights")
            render_insights(df, summary)

    with analytics_tab:
        st.subheader("Strategy and Exposure Analytics")
        render_group_charts(df)
        st.subheader("Strategy Performance Table")
        render_strategy_performance(project_root)
        st.subheader("Session Analysis")
        render_time_analysis(df)

    with controller_tab:
        render_controller_tab(cockpit_state, cockpit_url, cockpit_token)

    with blotter_tab:
        st.subheader("Execution Blotter")
        render_trade_blotter(df)

    with ops_tab:
        left, right = st.columns(2)
        with left:
            st.subheader("Data Quality and Source Health")
            render_operator_panel(df, file_path, candidate_files)
        with right:
            st.subheader("Runtime Monitor")
            render_runtime_monitor(runtime_snapshot, eod_summary)
        st.subheader("System Logs")
        render_logs_panel(recent_logs)


main()
