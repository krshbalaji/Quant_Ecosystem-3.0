from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
import json


class TelegramControlCenter:

    def __init__(self, runtime_state=None, orchestrator=None, execution_router=None):
        self.runtime_state = runtime_state
        self.orchestrator = orchestrator
        self.execution_router = execution_router

    def execute(self, command, router):
        raw = str(command).strip()
        parts = raw.lstrip("/").split()
        cmd = (parts[0] if parts else "").lower()
        if "@" in cmd:
            cmd = cmd.split("@", 1)[0]
        args = parts[1:]

        if cmd == "status":
            return self._status_report(router)
        if cmd == "system":
            return self._system_snapshot(router)
        if cmd == "positions":
            return router.get_positions_report()
        if cmd == "pnl":
            state = router.state
            return (
                f"PnL realized={round(float(state.realized_pnl), 2)} "
                f"unrealized={round(float(state.unrealized_pnl), 2)} "
                f"fees={round(float(state.fees_paid), 2)} "
                f"equity={round(float(state.equity), 2)}"
            )
        if cmd == "strategies":
            return self._strategies_report(router)
        if cmd == "strategy_status":
            return self._strategies_report(router)
        if cmd == "broker":
            return self._broker_report(router)
        if cmd == "market_hours":
            return self._market_hours_report(router)
        if cmd == "allocate":
            return self._allocate(router, args)
        if cmd == "activate_strategy":
            return self._cockpit_command(router, "ACTIVATE_STRATEGY", {"strategy_id": self._required_arg(args, "Usage: /activate_strategy <strategy_id>")})
        if cmd == "pause_strategy":
            return self._cockpit_command(router, "PAUSE_STRATEGY", {"strategy_id": self._required_arg(args, "Usage: /pause_strategy <strategy_id>")})
        if cmd == "retire_strategy":
            return self._cockpit_command(router, "RETIRE_STRATEGY", {"strategy_id": self._required_arg(args, "Usage: /retire_strategy <strategy_id>")})
        if cmd == "deploy_strategy":
            return self._deploy_strategy(router, args)
        if cmd == "manual":
            return self._set_mode(router, "MANUAL")
        if cmd == "assisted":
            return self._set_mode(router, "ASSISTED")
        if cmd == "autonomous":
            return self._set_mode(router, "AUTONOMOUS")
        if cmd in {"pause", "stop"}:
            return self._cockpit_command(router, "PAUSE_TRADING")
        if cmd in {"resume", "start"}:
            return self._cockpit_command(router, "START_TRADING")
        if cmd == "kill":
            return self._cockpit_command(router, "EMERGENCY_STOP")
        if cmd in {"stop", "stop_system"}:
            return self._stop_system_command(router, args)
        if cmd == "close_all":
            return self._cockpit_command(router, "CLOSE_ALL_POSITIONS")
        if cmd in {"rebalance", "force_rebalance"}:
            return self._cockpit_command(router, "FORCE_REBALANCE")
        if cmd == "reduce_exposure":
            return self._cockpit_command(router, "REDUCE_EXPOSURE")
        if cmd == "set_risk":
            if not args:
                return "Usage: /set_risk <risk_pct>"
            parsed = self._parse_float_arg(args[0], "Usage: /set_risk <risk_pct>")
            if isinstance(parsed, str):
                return parsed
            return self._cockpit_command(router, "SET_RISK_LEVEL", {"risk_pct": parsed})
        if cmd == "set_drawdown":
            if not args:
                return "Usage: /set_drawdown <max_drawdown_pct>"
            parsed = self._parse_float_arg(args[0], "Usage: /set_drawdown <max_drawdown_pct>")
            if isinstance(parsed, str):
                return parsed
            return self._cockpit_command(router, "SET_MAX_DRAWDOWN", {"max_drawdown_pct": parsed})
        if cmd == "set_multiplier":
            if not args:
                return "Usage: /set_multiplier <trade_size_multiplier>"
            parsed = self._parse_float_arg(args[0], "Usage: /set_multiplier <trade_size_multiplier>")
            if isinstance(parsed, str):
                return parsed
            return self._cockpit_command(router, "SET_TRADE_SIZE_MULTIPLIER", {"multiplier": parsed})
        if cmd == "execution_mode":
            if not args:
                return "Usage: /execution_mode <LOW_SLIPPAGE_MODE|BALANCED_MODE|AGGRESSIVE_MODE>"
            return self._cockpit_command(router, "SET_EXECUTION_MODE", {"mode": str(args[0]).upper()})
        if cmd == "report":
            return router.get_dashboard_report()
        if cmd == "why_trade":
            return self._why_trade(router)
        if cmd == "market_view":
            return self._market_view(router)
        if cmd == "next_move":
            return self._next_move(router)
        if cmd == "metabrain":
            return self._metabrain_report(router)
        if cmd == "cognitive":
            return self._cognitive_report(router)
        if cmd == "learning":
            return self._learning_report(router)
        if cmd == "lab_run":
            return self._lab_run(router, args)
        
        # Phase 1-3: Production Hardening Commands
        if cmd == "stop_system":
            return self._stop_system_command(router, args)
        if cmd == "drawdown":
            return self._drawdown_status(router)
        if cmd == "anomalies":
            return self._anomalies_status(router)
        if cmd == "cooldown_status":
            return self._cooldown_status(router)
        if cmd == "risk_status":
            return self._risk_status(router)
        if cmd == "safety":
            return self._safety_features_status(router)
        
        if cmd == "help":
            return self._help_text()

        return None

    def _close_all(self, router):
        positions = router.portfolio_engine.snapshot()
        if not positions:
            return "No open positions to close."

        closed = []
        for symbol in list(positions.keys()):
            try:
                router.broker.close_position(symbol)
                router.portfolio_engine.positions.pop(symbol, None)
                closed.append(symbol)
            except Exception:
                continue

        if router.reconciler:
            router.reconciler.reconcile(latest_prices=router.state.latest_prices)
        return f"Close all issued for {len(closed)} symbols: {', '.join(closed)}"

    def _strategies_report(self, router):
        bank = getattr(router, "strategy_bank_engine", None)
        selector_snapshot = dict(getattr(router, "_selector_last_snapshot", {}) or {})
        selector_line = self._selector_snapshot_line(selector_snapshot)
        if not bank or not getattr(bank, "enabled", False):
            base = router.get_strategy_report()
            return f"{selector_line}\n{base}" if selector_line else base

        rows = []
        try:
            rows = bank.registry.all()
        except Exception:
            rows = []

        if not rows:
            if selector_line:
                return f"{selector_line}\nStrategy Bank: no metadata yet."
            return "Strategy Bank: no metadata yet."

        rows = sorted(rows, key=lambda item: float(item.get("score", 0.0)), reverse=True)
        active_ids = set(bank.get_active_strategies())
        top = rows[:6]

        lines = ["Strategy Bank"]
        if selector_line:
            lines.append(selector_line)
        for row in top:
            sid = str(row.get("id", "?"))
            stage = str(row.get("stage", "CANDIDATE"))
            alloc = round(float(row.get("allocation_pct", bank.get_allocation(sid))), 2)
            cluster = str(row.get("correlation_cluster", "")) or "-"
            score = round(float(row.get("score", 0.0)), 2)
            active = "ON" if sid in active_ids else "OFF"
            reason = self._latest_transition_reason(sid)
            lines.append(
                f"{sid} | {stage} | {active} | alloc={alloc}% | score={score} | cluster={cluster}"
            )
            if reason:
                lines.append(f"  last: {reason}")

        if len(rows) > len(top):
            lines.append(f"... +{len(rows) - len(top)} more")
        return "\n".join(lines)

    def _status_report(self, router):
        base = router.get_status_report()
        selector_snapshot = dict(getattr(router, "_selector_last_snapshot", {}) or {})
        selector_line = self._selector_snapshot_line(selector_snapshot)
        if not selector_line:
            return base
        return f"{base}\n{selector_line}"

    def _selector_snapshot_line(self, snapshot):
        if not snapshot:
            return ""
        candidates = int(snapshot.get("candidate_count", len(snapshot.get("candidate_ids", []) or [])) or 0)
        selected = int(snapshot.get("selected_count", len(snapshot.get("selected_ids", []) or [])) or 0)
        blocked = dict(snapshot.get("blocked_reasons", {}) or {})
        if not blocked:
            return f"Selector cycle | candidates={candidates} selected={selected} blocked=0"
        sample = []
        for sid, reason in list(blocked.items())[:4]:
            sample.append(f"{sid}:{reason}")
        more = ""
        if len(blocked) > 4:
            more = f" (+{len(blocked) - 4} more)"
        return (
            f"Selector cycle | candidates={candidates} selected={selected} blocked={len(blocked)} "
            f"| blocked_reason={', '.join(sample)}{more}"
        )

    def _broker_report(self, router):
        state = getattr(router, "state", None)
        broker_router = getattr(router, "broker", None)
        broker_impl = getattr(broker_router, "broker", None) if broker_router else None

        broker_name = broker_impl.__class__.__name__ if broker_impl else "UnknownBroker"
        connected = bool(getattr(broker_impl, "connected", False)) if broker_impl else False
        source = str(getattr(state, "account_source", "UNKNOWN")) if state else "UNKNOWN"
        mode = str(getattr(state, "trading_mode", "UNKNOWN")) if state else "UNKNOWN"
        symbols = ",".join(list(getattr(router, "symbols", []) or [])[:4])
        if not symbols:
            symbols = "-"

        return (
            f"Broker={broker_name} "
            f"connected={connected} "
            f"source={source} "
            f"mode={mode} "
            f"symbols={symbols}"
        )

    def _market_hours_report(self, router):
        now_ist = self._now_ist(router)
        wd = now_ist.weekday()  # 0=Mon
        now_t = now_ist.time()

        strict = bool(getattr(getattr(router, "config", None), "strict_market_hours", False))
        status = {
            "CRYPTO:*": True,  # 24/7
            "NSE:*": (wd < 5 and dtime(9, 15) <= now_t <= dtime(15, 30)),
            "MCX:*": (wd < 5 and dtime(9, 0) <= now_t <= dtime(23, 30)),
            "FX:*": (wd < 5),
        }

        lines = [
            f"Market Hours | IST={now_ist.strftime('%Y-%m-%d %H:%M:%S')}",
            f"strict_gate={'ON' if strict else 'OFF'}",
        ]
        for prefix, is_open in status.items():
            lines.append(f"{prefix} {'OPEN' if is_open else 'CLOSED'}")
        return "\n".join(lines)

    def _now_ist(self, router):
        if hasattr(router, "_now_ist"):
            try:
                return router._now_ist()
            except Exception:
                pass
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo("Asia/Kolkata"))
        except Exception:
            ist = timezone(timedelta(hours=5, minutes=30))
            return datetime.now(ist)

    def _allocate(self, router, args):
        if len(args) < 2:
            return "Usage: /allocate <strategy_id> <percent>"
        strategy_id = str(args[0]).strip()
        try:
            pct = float(args[1])
        except ValueError:
            return "Invalid percent. Example: /allocate core_momentum_v1 25"
        return self._cockpit_command(router, "ADJUST_ALLOCATION", {"strategy_id": strategy_id, "allocation_pct": pct})

    def _deploy_strategy(self, router, args):
        if len(args) < 1:
            return "Usage: /deploy_strategy <strategy_id>"
        strategy_id = str(args[0]).strip()
        return self._cockpit_command(router, "ACTIVATE_STRATEGY", {"strategy_id": strategy_id})

    def _set_mode(self, router, mode):
        controller = getattr(router, "autonomous_controller", None)
        if not controller:
            return "Autonomous controller unavailable."
        return controller.set_mode(router, mode)

    def _required_arg(self, args, usage):
        if not args:
            raise ValueError(usage)
        value = str(args[0]).strip()
        if not value:
            raise ValueError(usage)
        return value

    def _parse_float_arg(self, raw, usage):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return usage

    def _cockpit_command(self, router, command, payload=None):
        try:
            from quant_ecosystem.research.cockpit.command_router import CockpitCommandRouter

            result = CockpitCommandRouter(router_provider=lambda: router).execute(command, payload or {})
            if not result.get("ok"):
                return f"{command}: {result.get('error', 'failed')}"
            body = result.get("result")
            if body is not None:
                return f"{command}: {body}"
            extras = {k: v for k, v in result.items() if k not in {"ok", "result"}}
            return f"{command}: {extras}" if extras else f"{command}: ok"
        except ValueError as exc:
            return str(exc)
        except Exception as exc:
            return f"{command}: {exc}"

    def _system_snapshot(self, router):
        try:
            from quant_ecosystem.operating.dashboard.system_state_api import SystemStateAPI

            state = SystemStateAPI(router_provider=lambda: router).get_system_state()
            market = state.get("market", {})
            portfolio = state.get("portfolio", {})
            engines = state.get("engines", {})
            on_count = sum(1 for payload in engines.values() if payload.get("status") == "ON")
            return (
                f"System Snapshot\n"
                f"online={state.get('online', False)} "
                f"regime={market.get('regime', 'UNKNOWN')} "
                f"equity={round(float(portfolio.get('equity', 0.0)), 2)} "
                f"open_positions={portfolio.get('open_positions', 0)} "
                f"drawdown={round(float(portfolio.get('drawdown_pct', 0.0)), 2)}%\n"
                f"engines_on={on_count}/{len(engines)}"
            )
        except Exception as exc:
            return f"System snapshot unavailable: {exc}"

    def _help_text(self):
        return (
            "🤖 *QUANT ECOSYSTEM 3.0 - TELEGRAM CONTROL*\n\n"
            "📊 *CORE COMMANDS*\n"
            "/start - 🚀 Start the trading system\n"
            "/stop - 🛑 Stop trading gracefully\n"
            "/pause - ⏸️ Pause trading temporarily\n"
            "/resume - ▶️ Resume trading\n"
            "/status - 📊 System status overview\n\n"
            "💰 *TRADING INFO*\n"
            "/dashboard - 🎛️ Interactive control panel\n"
            "/system - ⚙️ System snapshot\n"
            "/positions - 📍 Open positions\n"
            "/pnl - 💰 P&L summary\n"
            "/broker - 🏦 Broker status\n\n"
            "🎯 *SAFETY & RISK*\n"
            "/stop_system - 🛑 Safely shutdown all trading loops\n"
            "/drawdown - 📉 Current drawdown status\n"
            "/anomalies - 🚨 Anomaly detection\n"
            "/cooldown_status - ⏱️ Symbol cooldowns\n"
            "/safety - 🛡️ Active safety features\n\n"
            "🎛️ *TRADING CONTROL*\n"
            "/strategies - 🧠 Active strategies\n"
            "/pause_strategy <id> - ⏸️ Pause strategy\n"
            "/resume_strategy <id> - ▶️ Resume strategy\n"
            "/close_all - 📦 Close all positions\n"
            "/reduce_exposure - ⚠️ Reduce risk exposure\n\n"
            "🧠 *ADVANCED*\n"
            "/market_view - 🧠 Market intelligence\n"
            "/next_move - 🎯 Suggested next trade\n"
            "/metabrain - 🧬 Meta strategy decisions\n"
            "/cognitive - 🧠 Cognitive control\n\n"
            "_Use /dashboard for interactive control panel_"
        )

    def _why_trade(self, router):
        reason = str(getattr(router.state, "last_trade_explanation", "") or "No trade explanation available yet.")
        return f"Why trade\n{reason}"

    def _market_view(self, router):
        pre = dict(getattr(router.state, "pre_market_view", {}) or {})
        event = dict(getattr(router.state, "event_intelligence", {}) or {})
        return (
            f"Market View\n"
            f"bias={pre.get('market_bias', 'RANGE')} "
            f"vol={pre.get('volatility', 'LOW')} "
            f"risk={pre.get('risk_mode', 'RISK_ON')} "
            f"event={event.get('event_type', 'NONE')} "
            f"impact={event.get('impact', 'LOW')}"
        )

    def _next_move(self, router):
        plan = dict(getattr(router.state, "day_plan", {}) or {})
        symbols = list(plan.get("symbols", []) or [])
        strategies = list(plan.get("strategies", []) or [])
        risk_level = str(plan.get("risk_level", "MEDIUM"))
        if not symbols:
            return "Next move\nNo active day plan yet."
        symbol = symbols[0]
        strategy = strategies[0] if strategies else "fallback_trend"
        bias = str(getattr(router.state, "market_bias", "RANGE"))
        return (
            f"Next move\n"
            f"Trade {symbol} with {strategy}\n"
            f"Reason: {bias} bias with {risk_level} risk plan."
        )

    def _latest_transition_reason(self, strategy_id):
        folder = Path("reporting/output/strategy_transitions")
        if not folder.exists():
            return ""

        files = sorted(folder.glob("transitions_*.jsonl"), reverse=True)
        for file_path in files:
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for line in reversed(lines[-400:]):
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if str(event.get("strategy_id", "")) != strategy_id:
                    continue
                frm = str(event.get("from", "?"))
                to = str(event.get("to", "?"))
                reason = str(event.get("reason", ""))
                return f"{frm}->{to} ({reason})"
        return ""

    def _metabrain_report(self, router):
        brain = getattr(router, "meta_strategy_brain", None)
        if not brain:
            return "Meta Brain unavailable (ENABLE_META_STRATEGY_BRAIN=false)."

        decisions = getattr(brain, "last_decisions", {}) or {}
        if not decisions:
            return "Meta Brain active but no decisions yet."

        regime = decisions.get("regime", "UNKNOWN")
        active = decisions.get("ACTIVE_STRATEGIES", [])
        reduced = decisions.get("REDUCED_STRATEGIES", [])
        retired = decisions.get("RETIRED_STRATEGIES", [])
        promoted = decisions.get("PROMOTED_STRATEGIES", [])

        return (
            f"Meta Brain | regime={regime}\n"
            f"active={len(active)} {active}\n"
            f"reduced={len(reduced)} {reduced}\n"
            f"retired={len(retired)} {retired}\n"
            f"promoted={len(promoted)} {promoted}"
        )

    def _lab_run(self, router, args):
        controller = getattr(router, "strategy_lab_controller", None)
        if not controller:
            return "Strategy Lab unavailable (ENABLE_STRATEGY_LAB=false)."

        # Safe defaults for manual trigger.
        generate_count = 5
        variants = 3
        periods = 260
        try:
            if len(args) >= 1:
                generate_count = max(1, min(50, int(args[0])))
            if len(args) >= 2:
                variants = max(1, min(20, int(args[1])))
            if len(args) >= 3:
                periods = max(120, min(1000, int(args[2])))
        except ValueError:
            return "Usage: /lab_run [generate_count] [variants_per_base] [periods]"

        outcome = controller.run_experiment(
            generate_count=generate_count,
            variants_per_base=variants,
            periods=periods,
        )
        return (
            f"Lab batch complete | sandbox={outcome.get('sandbox_mode')}\n"
            f"research={len(outcome.get('NEW_RESEARCH_STRATEGIES', []))} "
            f"validated={len(outcome.get('VALIDATED_STRATEGIES', []))} "
            f"rejected={len(outcome.get('REJECTED_STRATEGIES', []))} "
            f"promoted={len(outcome.get('PROMOTED_STRATEGIES', []))}"
        )

    def _cognitive_report(self, router):
        controller = getattr(router, "cognitive_controller", None)
        if not controller:
            return "Cognitive Control unavailable (ENABLE_COGNITIVE_CONTROL=false)."

        snapshot = getattr(controller, "last_decision", {}) or {}
        if not snapshot:
            return "Cognitive Control active but no decision snapshot yet."

        decision = snapshot.get("decision", {}) or {}
        state = snapshot.get("state", {}) or {}
        memory = snapshot.get("memory", {}) or {}
        behavior = snapshot.get("behavior", {}) or {}

        return (
            f"Cognitive | mode={decision.get('system_mode', 'NA')} "
            f"risk={decision.get('portfolio_risk_level', 'NA')} "
            f"pref={decision.get('preferred_strategy_type', 'NA')}\n"
            f"actions={decision.get('actions', [])}\n"
            f"state: vol={round(float(state.get('volatility_level', 0.0)), 4)} "
            f"dd={round(float(state.get('portfolio_drawdown', 0.0)), 4)} "
            f"active={int(state.get('active_strategies', 0) or 0)} "
            f"lat_ms={round(float(state.get('execution_latency_ms', 0.0)), 2)}\n"
            f"memory: stress={int(memory.get('stress_events', 0) or 0)} "
            f"transitions={int(memory.get('regime_transitions', 0) or 0)}\n"
            f"behavior={behavior.get('applied', [])}"
        )

    def _learning_report(self, router):
        engine = getattr(router, "adaptive_learning_engine", None)
        if not engine:
            return "Adaptive Learning unavailable (ENABLE_ADAPTIVE_LEARNING=false)."

        payload = getattr(engine, "last_updates", {}) or {}
        if not payload:
            return "Adaptive Learning active but no updates yet."

        updates = list(payload.get("updates", []) or [])
        if not updates:
            return "Adaptive Learning: no strategy updates in latest snapshot."

        lines = [f"Learning updates={len(updates)}"]
        for item in updates[:5]:
            sid = str(item.get("strategy_id", "?"))
            score = round(float(item.get("learning_score", 0.0) or 0.0), 4)
            params = item.get("parameter_updates", {}) or {}
            regime_perf = item.get("regime_performance", {}) or {}
            best_regime = regime_perf.get("best_regime", "NA")
            lines.append(
                f"{sid} | learning_score={score} | best_regime={best_regime} | param_updates={len(params)}"
            )
        if len(updates) > 5:
            lines.append(f"... +{len(updates) - 5} more")
        return "\n".join(lines)

    # ========================================================================
    # PHASE 1-3: PRODUCTION HARDENING COMMANDS
    # ========================================================================

    def _stop_system_command(self, router, args):
        """Phase 1: Graceful shutdown via Telegram"""
        try:
            runtime_state = (
                getattr(router, "runtime_state", None)
                or getattr(self, "runtime_state", None)
                or getattr(getattr(router, "state", None), "runtime_state", None)
            )
            if runtime_state and hasattr(runtime_state, "stop"):
                runtime_state.stop()

            orchestrator = getattr(router, "orchestrator", None) or getattr(self, "orchestrator", None)
            if orchestrator and hasattr(orchestrator, "stop"):
                orchestrator.stop()

            execution_router = getattr(router, "execution_router", None) or getattr(self, "execution_router", None)
            if execution_router is not None:
                if hasattr(execution_router, "runtime_state") and execution_router.runtime_state and hasattr(execution_router.runtime_state, "stop"):
                    execution_router.runtime_state.stop()
                if hasattr(execution_router, "state") and execution_router.state and hasattr(execution_router.state, "runtime_state"):
                    execution_router.state.runtime_state = runtime_state
                if hasattr(execution_router, "stop"):
                    execution_router.stop()

            if getattr(router, "state", None) and hasattr(router.state, "runtime_state"):
                router.state.runtime_state = runtime_state

            reason = " ".join(args) if args else "Telegram command /stop_system"
            from quant_ecosystem.operating.core.shutdown_handler import request_shutdown
            request_shutdown(reason=reason)

            return "🛑 SYSTEM STOP INITIATED"
        except Exception as e:
            return f"Error initiating shutdown: {e}"

    def _drawdown_status(self, router):
        """Phase 2: Current drawdown and risk stage info"""
        try:
            from quant_ecosystem.operating.risk.dynamic_risk_scaler import get_dynamic_risk_scaler
            scaler = get_dynamic_risk_scaler()
            
            drawdown_pct = scaler.get_current_drawdown() * 100 if scaler.get_current_drawdown() else 0.0
            risk_scale = scaler.get_risk_scale_factor()
            stage_info = scaler.get_current_stage()
            stage = stage_info["stage"] if stage_info else "UNKNOWN"
            
            # Stage emoji based on risk level
            if stage == "CRITICAL":
                stage_emoji = "🔴"
            elif stage == "ELEVATED":
                stage_emoji = "🟡"
            else:
                stage_emoji = "🟢"
            
            peak_equity = scaler.get_peak_equity()
            current_equity = scaler.get_current_equity()
            
            return (
                f"{stage_emoji} DRAWDOWN STATUS\n"
                f"Current Stage: {stage}\n"
                f"Drawdown: {drawdown_pct:.2f}% (from peak)\n"
                f"Risk Scale Factor: {risk_scale:.2f}x\n"
                f"Position Sizing: {risk_scale*100:.0f}% of normal\n"
                f"Peak Equity: ${peak_equity:,.0f}\n"
                f"Current Equity: ${current_equity:,.0f}"
            )
        except Exception as e:
            return f"Drawdown status unavailable: {e}"

    def _anomalies_status(self, router):
        """Phase 2: Anomaly detection and kill switch status"""
        try:
            from quant_ecosystem.operating.risk.dynamic_risk_scaler import get_dynamic_risk_scaler
            scaler = get_dynamic_risk_scaler()
            anomaly_det = scaler.anomaly_detector
            kill_sw = scaler.kill_switch
            
            lines = ["🚨 ANOMALIES & EMERGENCY HALT"]
            
            # Consecutive losses
            consec_losses = anomaly_det.consecutive_losses
            loss_threshold = 5
            if consec_losses >= loss_threshold:
                lines.append(f"🔴 ANOMALY: Consecutive Losses={consec_losses} (threshold: {loss_threshold})")
            else:
                lines.append(f"🟢 Consecutive Losses={consec_losses}  ✓ OK")
            
            # Win rate
            recent_trades = len(anomaly_det.recent_wins_losses)
            if recent_trades > 0:
                win_rate = sum(anomaly_det.recent_wins_losses) / recent_trades * 100
                if win_rate < 35:
                    lines.append(f"🔴 ANOMALY: Win Rate={win_rate:.1f}% (threshold: 35%)")
                else:
                    lines.append(f"🟢 Win Rate={win_rate:.1f}% ✓ OK")
            else:
                lines.append(f"🟡 Win Rate: No trades yet")
            
            # Kill switch
            if kill_sw.is_triggered():
                lines.append(f"🔴 KILL SWITCH: ACTIVE")
                lines.append(f"   Reason: {kill_sw.trigger_reason}")
            else:
                lines.append(f"🟢 Kill Switch: ARMED (ready for emergency)")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Anomalies status unavailable: {e}"

    def _cooldown_status(self, router):
        """Phase 3: Per-symbol cooldown and trading constraints"""
        try:
            from quant_ecosystem.operating.execution.signal_diversity_engine import get_signal_diversity_engine
            diversity_engine = get_signal_diversity_engine()
            
            lines = ["🎯 TRADING CONSTRAINTS"]
            
            # Per-symbol cooldown details
            if hasattr(diversity_engine, 'per_symbol_cooldown') and diversity_engine.per_symbol_cooldown.symbol_history:
                cooldown_data = []
                for symbol, cycle_count in diversity_engine.per_symbol_cooldown.symbol_history.items():
                    remaining = max(0, 5 - cycle_count)
                    if remaining == 0:
                        cooldown_data.append(f"  {symbol}: 🟢 Ready")
                    else:
                        cooldown_data.append(f"  {symbol}: 🟡 Cooldown {remaining}c")
                
                lines.append(f"Per-Symbol Cooldown (5 cycles default):")
                lines.extend(cooldown_data[:5])  # Show first 5
                if len(cooldown_data) > 5:
                    lines.append(f"  ... and {len(cooldown_data)-5} more symbols")
            else:
                lines.append("Per-Symbol Cooldown: No recent trades")
            
            lines.append("")
            lines.append("Cycle Throttle: Max 3 trades/cycle")
            
            # Strategy diversity if available
            if hasattr(diversity_engine, 'signal_diversity_tracker'):
                tracker = diversity_engine.signal_diversity_tracker
                if hasattr(tracker, 'strategy_counts'):
                    total = sum(tracker.strategy_counts.values())
                    if total > 0:
                        trend_pct = (tracker.strategy_counts.get('TREND', 0) / total * 100)
                        mean_rev_pct = (tracker.strategy_counts.get('MEAN_REVERSION', 0) / total * 100)
                        breakout_pct = (tracker.strategy_counts.get('BREAKOUT', 0) / total * 100)
                        lines.append(f"Strategy Distribution: TREND={trend_pct:.0f}% | MEAN_REV={mean_rev_pct:.0f}% | BREAKOUT={breakout_pct:.0f}%")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Cooldown status unavailable: {e}"

    def _risk_status(self, router):
        """Phase 2: Detailed risk scaling information"""
        try:
            from quant_ecosystem.operating.risk.dynamic_risk_scaler import get_dynamic_risk_scaler
            scaler = get_dynamic_risk_scaler()
            
            lines = ["📊 DETAILED RISK STATUS"]
            lines.append("")
            
            # Stage thresholds
            lines.append("Risk Stages (Thresholds):")
            lines.append("  🟢 NORMAL: 0-15% DD → 1.0x scale (100%)")
            lines.append("  🟡 ELEVATED: 15-25% DD → 0.5x scale (50%)")
            lines.append("  🔴 CRITICAL: 25%+ DD → 0.25x scale (25%)")
            lines.append("")
            
            # Current state
            current_dd = scaler.get_current_drawdown() * 100 if scaler.get_current_drawdown() else 0.0
            current_stage = scaler.get_current_stage()
            stage_name = current_stage["stage"] if current_stage else "UNKNOWN"
            
            if stage_name == "CRITICAL":
                stage_emoji = "🔴"
            elif stage_name == "ELEVATED":
                stage_emoji = "🟡"
            else:
                stage_emoji = "🟢"
            
            lines.append(f"Current State:")
            lines.append(f"  {stage_emoji} Stage: {stage_name}")
            lines.append(f"  DD: {current_dd:.2f}%")
            lines.append(f"  Scale: {scaler.get_risk_scale_factor():.2f}x ({scaler.get_risk_scale_factor()*100:.0f}%)")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Risk status unavailable: {e}"

    def _safety_features_status(self, router):
        """Phase 1-3: All active safety features summary"""
        lines = ["🛡️ PRODUCTION SAFETY FEATURES (ACTIVE)"]
        lines.append("")
        
        lines.append("✅ PHASE 1: Graceful Shutdown")
        lines.append("   • Ctrl+C support (KeyboardInterrupt)")
        lines.append("   • Telegram /stop_system command")
        lines.append("   • Dashboard STOP button")
        lines.append("   • All background tasks respect shutdown flag")
        lines.append("")
        
        lines.append("✅ PHASE 2: Dynamic Risk Scaling & Anomaly Detection")
        lines.append("   • 3-stage risk scaling (NORMAL/ELEVATED/CRITICAL)")
        lines.append("   • Automatic position size reduction in drawdown")
        lines.append("   • Consecutive loss detection")
        lines.append("   • Win rate anomaly detection")
        lines.append("   • Global kill switch for emergency halt")
        lines.append("")
        
        lines.append("✅ PHASE 3: Signal Diversity & Trading Constraints")
        lines.append("   • Per-symbol trade cooldown (5 cycles)")
        lines.append("   • Max 3 trades per cycle throttle")
        lines.append("   • Strategy type distribution tracking")
        lines.append("   • Soft constraints (ignore signal, don't halt)")
        lines.append("")
        
        try:
            from quant_ecosystem.operating.core.shutdown_handler import get_shutdown_handler
            shutdown = get_shutdown_handler()
            status = "🟢 RUNNING" if shutdown.is_running() else "🔴 STOPPED"
            lines.append(f"System Status: {status}")
        except Exception:
            lines.append("System Status: Unknown")
        
        return "\n".join(lines)

    def consume_webhook_events(self):
        """Fallback polling loop."""
        if hasattr(self, "controller"):
            self.controller.consume_webhook_events()
