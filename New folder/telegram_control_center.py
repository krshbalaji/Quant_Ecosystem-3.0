from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
import json


class TelegramControlCenter:

    def execute(self, command, router):
        raw = str(command).strip()
        parts = raw.lstrip("/").split()
        cmd = (parts[0] if parts else "").lower()
        if "@" in cmd:
            cmd = cmd.split("@", 1)[0]
        args = parts[1:]

        if cmd == "status":
            return self._status_report(router)
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
        if cmd == "broker":
            return self._broker_report(router)
        if cmd == "market_hours":
            return self._market_hours_report(router)
        if cmd == "allocate":
            return self._allocate(router, args)
        if cmd == "deploy_strategy":
            return self._deploy_strategy(router, args)
        if cmd == "manual":
            return self._set_mode(router, "MANUAL")
        if cmd == "assisted":
            return self._set_mode(router, "ASSISTED")
        if cmd == "autonomous":
            return self._set_mode(router, "AUTONOMOUS")
        if cmd in {"pause", "stop"}:
            return router.stop_trading()
        if cmd in {"resume", "start"}:
            return router.start_trading()
        if cmd == "kill":
            return router.kill_switch()
        if cmd == "close_all":
            return self._close_all(router)
        if cmd == "report":
            return router.get_dashboard_report()
        if cmd == "metabrain":
            return self._metabrain_report(router)
        if cmd == "cognitive":
            return self._cognitive_report(router)
        if cmd == "learning":
            return self._learning_report(router)
        if cmd == "lab_run":
            return self._lab_run(router, args)

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
        controller = getattr(router, "autonomous_controller", None)
        if not controller:
            return "Autonomous controller unavailable."
        return controller.allocate(router, strategy_id, pct)

    def _deploy_strategy(self, router, args):
        if len(args) < 1:
            return "Usage: /deploy_strategy <strategy_id>"
        strategy_id = str(args[0]).strip()
        controller = getattr(router, "autonomous_controller", None)
        if not controller:
            return "Autonomous controller unavailable."
        return controller.deploy_strategy(router, strategy_id)

    def _set_mode(self, router, mode):
        controller = getattr(router, "autonomous_controller", None)
        if not controller:
            return "Autonomous controller unavailable."
        return controller.set_mode(router, mode)

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

    def consume_webhook_events(self):
        """Fallback polling loop."""
        if hasattr(self, "controller"):
            self.controller.consume_webhook_events()