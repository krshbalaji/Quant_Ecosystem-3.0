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
            return router.get_status_report()
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
        if not bank or not getattr(bank, "enabled", False):
            return router.get_strategy_report()

        rows = []
        try:
            rows = bank.registry.all()
        except Exception:
            rows = []

        if not rows:
            return "Strategy Bank: no metadata yet."

        rows = sorted(rows, key=lambda item: float(item.get("score", 0.0)), reverse=True)
        active_ids = set(bank.get_active_strategies())
        top = rows[:6]

        lines = ["Strategy Bank"]
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
