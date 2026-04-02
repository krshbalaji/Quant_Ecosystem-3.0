from quant_ecosystem.research.utils.decimal_utils import quantize


class SafetyLayer:

    def __init__(self, **kwargs):
        self.last_reason = ""

    def evaluate_cycle(self, router, cycle_result):
        mode = str(
            getattr(
                getattr(router, "state", None),
                "trading_mode",
                getattr(getattr(router, "config", None), "mode", "PAPER"),
            )
        ).upper()
        # Priority 1: kill switch state
        if router.state.trading_halted:
            self.last_reason = "KILL_SWITCH_OR_HALT_ACTIVE"
            return False, self.last_reason

        # Priority 2: abnormal pnl spike (absolute > 1.5% equity in one cycle)
        if cycle_result.get("status") == "TRADE":
            pnl_abs = float(cycle_result.get("pnl", 0.0))
            equity = float(router.state.equity or 0.0)
            if equity > 0:
                pnl_pct = abs((pnl_abs / equity) * 100.0)
                if pnl_pct > 1.5:
                    router.state.trading_enabled = False
                    self.last_reason = f"ABNORMAL_PNL_SPIKE_{quantize(pnl_pct, 4)}%"
                    return False, self.last_reason

        # Priority 3: broker connectivity
        if mode == "PAPER":
            self.last_reason = "OK"
            return True, self.last_reason
        try:
            broker = (
                getattr(getattr(router, "execution_router", None), "broker", None)
                or getattr(router, "_broker_router", None)
                or getattr(router, "_broker", None)
            )
            if broker is None:
                raise RuntimeError("missing broker")
            if hasattr(broker, "is_connected"):
                if not bool(broker.is_connected()):
                    raise RuntimeError("broker not connected")
            elif hasattr(broker, "get_balance"):
                broker.get_balance()
            else:
                raise RuntimeError("broker lacks connectivity interface")
        except Exception:
            router.state.trading_enabled = False
            self.last_reason = "BROKER_DISCONNECTED_AUTO_PAUSE"
            return False, self.last_reason

        self.last_reason = "OK"
        return True, self.last_reason
