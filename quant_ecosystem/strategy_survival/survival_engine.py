"""Strategy Survival Engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.strategy_survival.decay_detector import DecayDetector
from quant_ecosystem.strategy_survival.strategy_replacement_manager import StrategyReplacementManager


class StrategySurvivalEngine:
    """Continuously retires decaying strategies and promotes replacements."""

    def __init__(
        self,
        strategy_bank_layer=None,
        meta_strategy_brain=None,
        portfolio_ai=None,
        strategy_lab_controller=None,
        decay_detector: Optional[DecayDetector] = None,
        replacement_manager: Optional[StrategyReplacementManager] = None,
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.meta_strategy_brain = meta_strategy_brain
        self.portfolio_ai = portfolio_ai
        self.strategy_lab_controller = strategy_lab_controller
        self.decay_detector = decay_detector or DecayDetector()
        self.replacement_manager = replacement_manager or StrategyReplacementManager()
        self.last_report: Dict = {}

    def run_cycle(self, strategy_rows: Optional[Iterable[Dict]] = None) -> Dict:
        """Evaluate all strategies and apply survival lifecycle actions."""
        rows = list(strategy_rows) if strategy_rows is not None else self._fetch_rows()
        if not rows:
            report = {"decaying": [], "reduced": [], "retired": [], "replacements": []}
            self.last_report = report
            return report

        replacement_pool = self._load_replacement_pool()
        existing_ids = {str(row.get("id", "")).strip() for row in rows if row.get("id")}

        updated_rows: List[Dict] = []
        decaying_ids: List[str] = []
        reduced_ids: List[str] = []
        retired_ids: List[str] = []
        replacement_ids: List[str] = []
        promoted_rows: List[Dict] = []

        for row in rows:
            sid = str(row.get("id", "")).strip()
            if not sid:
                continue
            decay_report = self.decay_detector.evaluate(row)
            if decay_report.get("is_decaying", False):
                decaying_ids.append(sid)

            decision = self.replacement_manager.apply(
                strategy_row=row,
                decay_report=decay_report,
                replacement_pool=replacement_pool,
                existing_ids=existing_ids,
            )
            updated = dict(decision.get("row", row))
            action = str(decision.get("action", "STABLE")).upper()
            updated["survival_action"] = action
            updated["survival_decay_report"] = decay_report
            updated_rows.append(updated)

            if action == "REDUCE":
                reduced_ids.append(sid)
            elif action == "RETIRE":
                retired_ids.append(sid)

            replacement = decision.get("replacement")
            if replacement:
                rep_id = str(replacement.get("id", "")).strip()
                if rep_id and rep_id not in existing_ids and rep_id not in replacement_ids:
                    replacement_ids.append(rep_id)
                    promoted_rows.append(replacement)
                    existing_ids.add(rep_id)

        # Persist strategy changes and promoted replacements.
        final_rows = updated_rows + promoted_rows
        self._persist_rows(final_rows)
        self._publish_to_meta_brain(decaying_ids, reduced_ids, retired_ids, replacement_ids)
        self._publish_to_portfolio_ai(retired_ids, replacement_ids)

        report = {
            "decaying": decaying_ids,
            "reduced": reduced_ids,
            "retired": retired_ids,
            "replacements": replacement_ids,
            "updated_count": len(updated_rows),
            "promoted_count": len(promoted_rows),
        }
        self.last_report = report
        return report

    def _fetch_rows(self) -> List[Dict]:
        layer = self.strategy_bank_layer
        if not (layer and hasattr(layer, "is_enabled") and layer.is_enabled()):
            return []
        try:
            return list(layer.registry_rows())
        except Exception:
            return []

    def _persist_rows(self, rows: List[Dict]) -> None:
        layer = self.strategy_bank_layer
        if not (layer and hasattr(layer, "is_enabled") and layer.is_enabled()):
            return
        try:
            registry = layer.bank_engine.registry
            for row in rows:
                sid = str(row.get("id", "")).strip()
                if not sid:
                    continue
                registry.upsert(dict(row))
            registry.save()
        except Exception:
            return

    def _publish_to_meta_brain(self, decaying, reduced, retired, replacements) -> None:
        brain = self.meta_strategy_brain
        if brain is None:
            return
        payload = {
            "decaying": list(decaying),
            "reduced": list(reduced),
            "retired": list(retired),
            "replacements": list(replacements),
        }
        try:
            setattr(brain, "last_survival_decision", payload)
        except Exception:
            return

    def _publish_to_portfolio_ai(self, retired_ids: List[str], replacement_ids: List[str]) -> None:
        engine = self.portfolio_ai
        if engine is None:
            return
        try:
            alloc = dict(getattr(engine, "last_allocation", {}) or {})
            for sid in retired_ids:
                if sid in alloc:
                    alloc[sid] = 0.0
            # New replacements start at zero until regular allocator cycle.
            for sid in replacement_ids:
                alloc.setdefault(sid, 0.0)
            setattr(engine, "last_allocation", alloc)
            setattr(
                engine,
                "last_survival_adjustment",
                {"retired": list(retired_ids), "introduced": list(replacement_ids)},
            )
        except Exception:
            return

    def _load_replacement_pool(self) -> List[Dict]:
        # Prefer Strategy Lab validated set when available.
        ctrl = self.strategy_lab_controller
        if ctrl and hasattr(ctrl, "repository") and getattr(ctrl, "repository", None):
            base = Path(getattr(ctrl.repository, "validated_dir", "strategy_lab/validated_strategies"))
            rows = self._read_json_dir(base)
            if rows:
                return rows
        # Fallback path.
        return self._read_json_dir(Path("strategy_lab/validated_strategies"))

    def _read_json_dir(self, folder: Path) -> List[Dict]:
        if not folder.exists():
            return []
        out = []
        for path in sorted(folder.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            payload.setdefault("id", path.stem)
            out.append(payload)
        return out



# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class SurvivalEngine:
    """Minimal SystemFactory entry-point for strategy survival.

    Delegates to :class:`StrategySurvivalEngine` when available.
    """

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = StrategySurvivalEngine()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("SurvivalEngine: delegate unavailable (%s) — stub mode", exc)
        self._log.info("SurvivalEngine initialized")

    def remove_weak(self, strategies: list, threshold: float = 0.0) -> list:
        """Retire strategies whose score falls below *threshold*.

        Returns the survivors; falls back to the full list on error.
        """
        if self._delegate is not None:
            try:
                return self._delegate.run_survival_cycle(
                    strategies=strategies, min_score=threshold
                )
            except Exception as exc:  # noqa: BLE001
                self._log.warning("SurvivalEngine.remove_weak: delegate error (%s)", exc)
        # Stub: keep strategies with score > threshold if available
        survivors = []
        for s in strategies:
            score = s.get("score", 1.0) if isinstance(s, dict) else 1.0
            if score >= threshold:
                survivors.append(s)
        return survivors if survivors else list(strategies)
