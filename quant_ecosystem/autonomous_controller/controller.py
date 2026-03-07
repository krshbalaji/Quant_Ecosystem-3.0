"""Autonomous controller for operational modes and deployment actions."""


class AutonomousController:
    """Controls Manual / Assisted / Autonomous behavior and strategy actions."""

    MODES = {"MANUAL", "ASSISTED", "AUTONOMOUS"}

    def __init__(self, **kwargs):
        self.mode = "AUTONOMOUS"

    def set_mode(self, router, mode):
        normalized = str(mode).strip().upper()
        if normalized not in self.MODES:
            return f"Invalid mode: {mode}. Use MANUAL/ASSISTED/AUTONOMOUS."

        self.mode = normalized
        if normalized == "MANUAL":
            router.state.auto_mode = False
            router.state.trading_enabled = False
            return "Mode set to MANUAL (auto execution off)."
        if normalized == "ASSISTED":
            router.state.auto_mode = False
            router.state.trading_enabled = True
            return "Mode set to ASSISTED (manual signal confirmation mode)."

        router.state.auto_mode = True
        router.state.trading_enabled = True
        return "Mode set to AUTONOMOUS (full automation on)."

    def allocate(self, router, strategy_id, pct):
        allocator = getattr(router, "capital_allocator_layer", None)
        if not allocator:
            return "Allocator layer unavailable."
        value = allocator.set_manual_allocation(strategy_id, pct)
        return f"Allocation override set: {strategy_id}={value}%"

    def deploy_strategy(self, router, strategy_id):
        bank = getattr(router, "strategy_bank_engine", None)
        engine = getattr(router, "strategy_engine", None)

        if not engine:
            return "Strategy engine unavailable."

        available = {item.get("id") for item in (engine.strategies or [])}
        sid = str(strategy_id).strip()
        if sid not in available:
            return f"Strategy not found: {sid}"

        if bank and getattr(bank, "enabled", False):
            row = bank.registry.get(sid) or {"id": sid}
            row["stage"] = "LIVE"
            row["active"] = True
            bank.registry.upsert(row)
            bank.registry.save()

        active = set(getattr(engine, "active_ids", set()) or set())
        active.add(sid)
        engine.active_ids = active
        return f"Strategy deployed to active set: {sid}"
