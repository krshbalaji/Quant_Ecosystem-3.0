class TelegramControlCenter:

    def execute(self, command, router):
        cmd = str(command).strip().lower().lstrip("/")

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
            return router.get_strategy_report()
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
