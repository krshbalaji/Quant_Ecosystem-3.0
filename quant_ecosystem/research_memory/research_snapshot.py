"""
quant_ecosystem/research_memory/research_snapshot.py
=====================================================
Research Snapshot — Quant Ecosystem 3.0

A snapshot captures the complete state of the research memory layer at a
single point in time.  Institutional quant funds take daily or weekly
snapshots so they can:

• Audit the exact state of the strategy universe at any past date
• Roll back to a known-good state if a bug corrupts the live registry
• Compare strategy populations across quarters to measure evolution quality
• Reproduce a specific live deployment state for post-mortem analysis

Architecture
------------
SnapshotManifest   — lightweight index entry for a snapshot
ResearchSnapshot   — full snapshot payload (can be gigabytes when serialised)
SnapshotStore      — persistent façade (create / load / diff / restore)

Storage layout
--------------
    <root>/snapshots/
        index.jsonl             — append-only index of all snapshots
        <snapshot_id>/
            manifest.json       — metadata + statistics
            alphas.json         — all AlphaRecord dicts
            genealogy.json      — all GenealogyNode dicts
            performance.json    — all StrategyArchive summaries
            experiments.json    — all ExperimentRecord dicts (optional, can be large)

Integration points
------------------
• ResearchMemoryLayer.snapshot()     — one-call capture of the full layer
• core.master_orchestrator          — schedule daily snapshot in post-market phase
• core.system_factory               — load most-recent snapshot on boot to warm caches
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Metadata objects
# ---------------------------------------------------------------------------

@dataclass
class SnapshotManifest:
    """Lightweight index entry stored in snapshots/index.jsonl."""

    snapshot_id:        str
    label:              str             = ""        # e.g. "eod_2026_03_07"
    trigger:            str             = "manual"  # manual|scheduled|event
    created_at:         str             = ""

    # Counts (for fast filtering without loading payloads)
    alpha_count:        int             = 0
    live_alpha_count:   int             = 0
    strategy_count:     int             = 0
    experiment_count:   int             = 0
    regime_count:       int             = 0

    # Summary metrics
    avg_sharpe:         float           = 0.0
    best_sharpe:        float           = 0.0

    # System state at snapshot time
    quant_mode:         str             = "PAPER"
    git_hash:           str             = ""
    notes:              str             = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "SnapshotManifest":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class ResearchSnapshot:
    """Full research state snapshot."""

    manifest:           SnapshotManifest
    alphas:             List[Dict]      = field(default_factory=list)
    genealogy_nodes:    List[Dict]      = field(default_factory=list)
    performance_slices: List[Dict]      = field(default_factory=list)
    experiments:        List[Dict]      = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "snapshot_id":    self.manifest.snapshot_id,
            "label":          self.manifest.label,
            "created_at":     self.manifest.created_at,
            "alpha_count":    len(self.alphas),
            "strategy_count": self.manifest.strategy_count,
            "avg_sharpe":     self.manifest.avg_sharpe,
        }


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

_NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class SnapshotStore:
    """
    Creates, stores, and retrieves research snapshots.

    Usage
    -----
        # Minimal wiring — pass the three memory stores
        store = SnapshotStore(root="data/snapshots")

        snapshot = store.create(
            alpha_store   = alpha_memory_store,
            genealogy     = strategy_genealogy,
            perf_archive  = performance_archive,
            tracker       = experiment_tracker,  # optional — can be large
            label         = "eod_2026_03_07",
            trigger       = "scheduled",
        )

        # Load a past snapshot
        loaded = store.load(snapshot_id)

        # Compare two snapshots
        diff = store.diff(snapshot_id_a, snapshot_id_b)

        # List recent snapshots
        recent = store.list_snapshots(limit=10)
    """

    _INDEX_FILE = "index.jsonl"

    def __init__(
        self,
        root:   str = "data/snapshots",
        config: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        if config and isinstance(config, dict):
            root = config.get("SNAPSHOT_ROOT", root)

        self._root  = Path(root)
        self._lock  = threading.RLock()
        self._index: List[SnapshotManifest] = []

        self._root.mkdir(parents=True, exist_ok=True)
        self._rebuild_index()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        alpha_store  = None,
        genealogy    = None,
        perf_archive = None,
        tracker      = None,
        label:  str  = "",
        trigger: str = "manual",
        notes:  str  = "",
        include_experiments: bool = True,
        quant_mode: str = "PAPER",
    ) -> ResearchSnapshot:
        """
        Capture the current state of the research memory layer.

        Parameters
        ----------
        alpha_store         AlphaMemoryStore instance
        genealogy           StrategyGenealogy instance
        perf_archive        PerformanceArchive instance
        tracker             ExperimentTracker instance (optional)
        label               Human-readable label for this snapshot
        trigger             'manual' | 'scheduled' | 'event'
        include_experiments Whether to include experiment records (can be large)
        """
        sid = f"snap_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        alphas      = self._capture_alphas(alpha_store)
        nodes       = self._capture_genealogy(genealogy)
        slices      = self._capture_performance(perf_archive)
        experiments = self._capture_experiments(tracker) if include_experiments and tracker else []

        # Compute summary stats
        sharpes         = [a.get("sharpe", 0) for a in alphas if a.get("sharpe", 0) > 0]
        live_alpha_count = sum(1 for a in alphas if a.get("status") == "live")
        regimes          = {a.get("regime", "all") for a in alphas}

        manifest = SnapshotManifest(
            snapshot_id      = sid,
            label            = label or f"snap_{time.strftime('%Y_%m_%d')}",
            trigger          = trigger,
            created_at       = _NOW(),
            alpha_count      = len(alphas),
            live_alpha_count = live_alpha_count,
            strategy_count   = len(nodes),
            experiment_count = len(experiments),
            regime_count     = len(regimes),
            avg_sharpe       = round(sum(sharpes) / len(sharpes), 4) if sharpes else 0.0,
            best_sharpe      = round(max(sharpes), 4) if sharpes else 0.0,
            quant_mode       = quant_mode,
            git_hash         = self._git_hash(),
            notes            = notes,
        )

        snap = ResearchSnapshot(
            manifest          = manifest,
            alphas            = alphas,
            genealogy_nodes   = nodes,
            performance_slices = slices,
            experiments       = experiments,
        )

        with self._lock:
            self._write_snapshot(snap)
            self._index.append(manifest)
            self._append_index(manifest)

        return snap

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, snapshot_id: str) -> Optional[ResearchSnapshot]:
        """Load a full snapshot from disk."""
        snap_dir = self._root / snapshot_id
        if not snap_dir.exists():
            return None
        try:
            manifest_d = json.loads((snap_dir / "manifest.json").read_text())
            manifest   = SnapshotManifest.from_dict(manifest_d)

            alphas  = self._load_json(snap_dir / "alphas.json")
            nodes   = self._load_json(snap_dir / "genealogy.json")
            slices  = self._load_json(snap_dir / "performance.json")
            exps    = self._load_json(snap_dir / "experiments.json")

            return ResearchSnapshot(
                manifest          = manifest,
                alphas            = alphas,
                genealogy_nodes   = nodes,
                performance_slices = slices,
                experiments       = exps,
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Query / diff
    # ------------------------------------------------------------------

    def list_snapshots(self, limit: int = 50, trigger: Optional[str] = None) -> List[SnapshotManifest]:
        snaps = list(reversed(self._index))
        if trigger:
            snaps = [s for s in snaps if s.trigger == trigger]
        return snaps[:limit]

    def latest(self) -> Optional[SnapshotManifest]:
        return self._index[-1] if self._index else None

    def diff(self, snap_id_a: str, snap_id_b: str) -> Dict[str, Any]:
        """
        Compare two snapshots. Returns a summary of what changed.
        """
        a = self.load(snap_id_a)
        b = self.load(snap_id_b)

        if a is None or b is None:
            return {"error": "one or both snapshots not found"}

        ids_a = {r["strategy_id"] for r in a.alphas}
        ids_b = {r["strategy_id"] for r in b.alphas}

        new_alphas     = ids_b - ids_a
        retired_alphas = ids_a - ids_b
        common         = ids_a & ids_b

        # Sharpe changes for common strategies
        sharpe_a = {r["strategy_id"]: r.get("sharpe", 0) for r in a.alphas}
        sharpe_b = {r["strategy_id"]: r.get("sharpe", 0) for r in b.alphas}
        improved  = {sid for sid in common if sharpe_b.get(sid, 0) > sharpe_a.get(sid, 0) + 0.05}
        degraded  = {sid for sid in common if sharpe_b.get(sid, 0) < sharpe_a.get(sid, 0) - 0.05}

        return {
            "snapshot_a":        snap_id_a,
            "snapshot_b":        snap_id_b,
            "date_a":            a.manifest.created_at,
            "date_b":            b.manifest.created_at,
            "new_alphas":        sorted(new_alphas),
            "retired_alphas":    sorted(retired_alphas),
            "improved_alphas":   sorted(improved),
            "degraded_alphas":   sorted(degraded),
            "alpha_count_delta": len(ids_b) - len(ids_a),
            "avg_sharpe_a":      a.manifest.avg_sharpe,
            "avg_sharpe_b":      b.manifest.avg_sharpe,
            "sharpe_delta":      round(b.manifest.avg_sharpe - a.manifest.avg_sharpe, 4),
        }

    def restore_alpha_list(self, snapshot_id: str) -> List[Dict]:
        """
        Return the list of alpha dicts from a past snapshot.
        Used to roll back the alpha registry to a known-good state.
        """
        snap = self.load(snapshot_id)
        return snap.alphas if snap else []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _capture_alphas(alpha_store) -> List[Dict]:
        if alpha_store is None:
            return []
        try:
            return [r.to_dict() for r in alpha_store.all_alphas()]
        except Exception:
            return []

    @staticmethod
    def _capture_genealogy(genealogy) -> List[Dict]:
        if genealogy is None:
            return []
        try:
            return [n.to_dict() for n in genealogy._tree.all_nodes()]
        except Exception:
            return []

    @staticmethod
    def _capture_performance(perf_archive) -> List[Dict]:
        if perf_archive is None:
            return []
        try:
            slices = []
            for arch in perf_archive._cache.values():
                for sl in arch.slices:
                    slices.append(sl.to_dict())
            return slices
        except Exception:
            return []

    @staticmethod
    def _capture_experiments(tracker) -> List[Dict]:
        if tracker is None:
            return []
        try:
            return [e.to_dict() for e in tracker._exps.values()]
        except Exception:
            return []

    def _write_snapshot(self, snap: ResearchSnapshot) -> None:
        snap_dir = self._root / snap.manifest.snapshot_id
        snap_dir.mkdir(exist_ok=True)

        def _write(path: Path, data: Any) -> None:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(path)

        _write(snap_dir / "manifest.json",    snap.manifest.to_dict())
        _write(snap_dir / "alphas.json",      snap.alphas)
        _write(snap_dir / "genealogy.json",   snap.genealogy_nodes)
        _write(snap_dir / "performance.json", snap.performance_slices)
        _write(snap_dir / "experiments.json", snap.experiments)

    def _append_index(self, manifest: SnapshotManifest) -> None:
        line = json.dumps(manifest.to_dict())
        with open(self._root / self._INDEX_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _rebuild_index(self) -> None:
        idx_path = self._root / self._INDEX_FILE
        if not idx_path.exists():
            return
        for line in idx_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self._index.append(SnapshotManifest.from_dict(json.loads(line)))
            except Exception:
                pass

    @staticmethod
    def _load_json(path: Path) -> List:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def _git_hash() -> str:
        try:
            import subprocess
            r = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=2,
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""
