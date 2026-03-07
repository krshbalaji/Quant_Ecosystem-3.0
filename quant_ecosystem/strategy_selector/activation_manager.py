"""Strategy activation/deactivation manager."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set


class ActivationManager:
    """Controls active strategy set with safety limits."""

    def __init__(self, strategy_engine=None, strategy_bank_engine=None, max_active_strategies: int = 5, **kwargs):
        self.strategy_engine = strategy_engine
        self.strategy_bank_engine = strategy_bank_engine
        self.max_active_strategies = max(1, int(max_active_strategies))

    def activate_strategy(self, name: str) -> str:
        if not self.strategy_engine:
            return "Strategy engine unavailable."
        sid = str(name).strip()
        executable_universe = self._executable_universe()
        if executable_universe and sid not in executable_universe:
            return f"Activation blocked: {sid} is not executable in live strategy engine."
        active = set(getattr(self.strategy_engine, "active_ids", set()) or set())
        if sid in active:
            return f"{sid} already active."
        if len(active) >= self.max_active_strategies:
            return f"Activation blocked: max_active_strategies={self.max_active_strategies}"
        active.add(sid)
        self.strategy_engine.active_ids = active
        self._set_bank_active(sid, True)
        return f"Activated {sid}."

    def deactivate_strategy(self, name: str) -> str:
        if not self.strategy_engine:
            return "Strategy engine unavailable."
        sid = str(name).strip()
        active = set(getattr(self.strategy_engine, "active_ids", set()) or set())
        if sid not in active:
            return f"{sid} already inactive."
        active.remove(sid)
        self.strategy_engine.active_ids = active
        self._set_bank_active(sid, False)
        return f"Deactivated {sid}."

    def apply_selection(self, selected_ids: Iterable[str], available_ids: Iterable[str] | None = None) -> Dict:
        if not self.strategy_engine:
            return {"activated": [], "deactivated": [], "active_ids": []}

        target: List[str] = []
        for sid in selected_ids:
            name = str(sid).strip()
            if name and name not in target:
                target.append(name)
        target = target[: self.max_active_strategies]
        target_set = set(target)

        executable_universe = self._executable_universe()
        if available_ids is None:
            universe = set(executable_universe)
        else:
            requested_universe = {str(sid).strip() for sid in available_ids if str(sid).strip()}
            universe = requested_universe & executable_universe if executable_universe else requested_universe

        current: Set[str] = set(getattr(self.strategy_engine, "active_ids", set()) or set())
        # Safety: only keep executable target strategies.
        target_set = {sid for sid in target_set if sid in universe}
        if not target_set:
            # Preserve currently active executable strategies instead of dropping to zero.
            target_set = {sid for sid in current if sid in universe}
            if not target_set and universe:
                fallback_id = str(getattr(self.strategy_engine, "fallback_id", "")).strip()
                if fallback_id in universe:
                    target_set = {fallback_id}
                else:
                    target_set = {sorted(universe)[0]}

        deactivated = sorted([sid for sid in current if sid not in target_set])
        activated = sorted([sid for sid in target_set if sid not in current and sid in universe])

        new_active = set(current)
        for sid in deactivated:
            new_active.discard(sid)
            self._set_bank_active(sid, False)
        for sid in activated:
            new_active.add(sid)
            self._set_bank_active(sid, True)

        self.strategy_engine.active_ids = new_active
        return {
            "activated": activated,
            "deactivated": deactivated,
            "active_ids": sorted(new_active),
        }

    def _executable_universe(self) -> Set[str]:
        return {
            str(item.get("id")).strip()
            for item in (getattr(self.strategy_engine, "strategies", []) or [])
            if str(item.get("id", "")).strip()
        }

    def _set_bank_active(self, strategy_id: str, active: bool) -> None:
        bank = self.strategy_bank_engine
        if not bank or not getattr(bank, "enabled", False):
            return
        row = bank.registry.get(strategy_id) or {"id": strategy_id}
        row["active"] = bool(active)
        bank.registry.upsert(row)
        bank.registry.save()
