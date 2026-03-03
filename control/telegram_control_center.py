from pathlib import Path
import json


class TelegramControlCenter:

    def execute(self, command, router):
        raw = str(command).strip()
        parts = raw.lstrip("/").split()
        cmd = (parts[0] if parts else "").lower()
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
