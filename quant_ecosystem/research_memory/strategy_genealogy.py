"""
quant_ecosystem/research_memory/strategy_genealogy.py
======================================================
Strategy Genealogy — Quant Ecosystem 3.0

Tracks the complete parent → child evolution tree for every strategy in the
ecosystem.  Mirrors the concept used in evolutionary computation and genetic
algorithms where knowing an organism's lineage explains its behaviour.

Genealogy enables
-----------------
• Explaining *why* a strategy performs well (which ancestor introduced the key parameter)
• Calculating family-level diversity to prevent over-fitting to one lineage
• Retiring an entire subtree when a critical ancestor is found to be flawed
• Replaying the exact sequence of mutations that produced a winning alpha

Storage layout
--------------
    <root>/genealogy/
        nodes.jsonl        — append-only log of every node write
        <strategy_id>.json — latest snapshot of each node

Design
------
GenealogyNode      — one node in the tree (one strategy)
GenealogyTree      — in-memory tree structure (rebuilt from disk)
StrategyGenealogy  — persistent façade (read / write / traverse)
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@dataclass
class GenealogyNode:
    """
    One node in the strategy evolution tree.

    parent_id = None  →  seed strategy (no ancestor)
    parent_id = X     →  mutated or crossed from X
    """

    # --- Identity ---
    strategy_id:    str
    parent_id:      Optional[str]  = None
    parent_ids:     List[str]      = field(default_factory=list)   # for crossover (2 parents)
    generation:     int            = 0
    family:         str            = "unknown"

    # --- Mutation metadata ---
    mutation_type:  str            = "seed"     # seed | mutation | crossover | ingestion
    mutation_ops:   List[str]      = field(default_factory=list)   # list of ops applied
    parameter_delta: Dict[str, Any] = field(default_factory=dict)  # changed params

    # --- Performance at birth (backtest metrics) ---
    birth_sharpe:   float          = 0.0
    birth_drawdown: float          = 0.0
    birth_regime:   str            = "all"

    # --- Lifecycle ---
    status:         str            = "discovered"   # discovered|shadow|live|retired
    created_at:     str            = ""
    retired_at:     str            = ""
    retire_reason:  str            = ""

    # --- Children (maintained by GenealogyTree) ---
    child_ids:      List[str]      = field(default_factory=list)

    # --- Free-form ---
    notes:          str            = ""
    tags:           List[str]      = field(default_factory=list)

    def is_seed(self) -> bool:
        return self.parent_id is None and not self.parent_ids

    def all_parent_ids(self) -> List[str]:
        """Combined list: primary parent + crossover parents."""
        seen: Set[str] = set()
        result = []
        for pid in ([self.parent_id] if self.parent_id else []) + self.parent_ids:
            if pid and pid not in seen:
                seen.add(pid)
                result.append(pid)
        return result

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "GenealogyNode":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------

class GenealogyTree:
    """
    In-memory directed acyclic graph of strategy evolution.

    Nodes are GenealogyNode instances.
    Edges: parent_id → strategy_id  (parent produced child via mutation)
    """

    def __init__(self) -> None:
        self._nodes:    Dict[str, GenealogyNode] = {}
        self._children: Dict[str, List[str]]     = defaultdict(list)   # parent → [children]
        self._families: Dict[str, List[str]]     = defaultdict(list)   # family → [ids]

    def add(self, node: GenealogyNode) -> None:
        sid = node.strategy_id
        self._nodes[sid] = node

        for pid in node.all_parent_ids():
            if sid not in self._children[pid]:
                self._children[pid].append(sid)
            # Back-fill parent's child_ids if the parent node is loaded
            parent_node = self._nodes.get(pid)
            if parent_node and sid not in parent_node.child_ids:
                parent_node.child_ids.append(sid)

        if sid not in self._families[node.family]:
            self._families[node.family].append(sid)

    def get(self, strategy_id: str) -> Optional[GenealogyNode]:
        return self._nodes.get(strategy_id)

    def ancestors(self, strategy_id: str, max_depth: int = 50) -> List[GenealogyNode]:
        """Return all ancestors in BFS order (nearest first)."""
        result: List[GenealogyNode] = []
        visited: Set[str] = set()
        queue: deque = deque()

        node = self._nodes.get(strategy_id)
        if node is None:
            return []

        for pid in node.all_parent_ids():
            if pid not in visited:
                queue.append((pid, 1))

        while queue and len(result) < max_depth:
            pid, depth = queue.popleft()
            if pid in visited or depth > max_depth:
                continue
            visited.add(pid)
            pnode = self._nodes.get(pid)
            if pnode:
                result.append(pnode)
                for gp in pnode.all_parent_ids():
                    if gp not in visited:
                        queue.append((gp, depth + 1))
        return result

    def descendants(self, strategy_id: str, max_depth: int = 50) -> List[GenealogyNode]:
        """Return all descendants (BFS, nearest first)."""
        result: List[GenealogyNode] = []
        visited: Set[str] = set()
        queue: deque = deque([(cid, 1) for cid in self._children.get(strategy_id, [])])

        while queue and len(result) < 500:
            cid, depth = queue.popleft()
            if cid in visited or depth > max_depth:
                continue
            visited.add(cid)
            cnode = self._nodes.get(cid)
            if cnode:
                result.append(cnode)
                for gc in self._children.get(cid, []):
                    if gc not in visited:
                        queue.append((gc, depth + 1))
        return result

    def lineage_path(self, strategy_id: str) -> List[GenealogyNode]:
        """
        Return the single primary lineage path from the oldest seed to this node.
        Uses primary parent_id only (not crossover parents).
        """
        path: List[GenealogyNode] = []
        current = self._nodes.get(strategy_id)
        visited: Set[str] = set()

        while current and current.strategy_id not in visited:
            path.append(current)
            visited.add(current.strategy_id)
            if current.parent_id:
                current = self._nodes.get(current.parent_id)
            else:
                break

        path.reverse()
        return path

    def family_members(self, family: str) -> List[GenealogyNode]:
        return [self._nodes[i] for i in self._families.get(family, []) if i in self._nodes]

    def seed_nodes(self) -> List[GenealogyNode]:
        return [n for n in self._nodes.values() if n.is_seed()]

    def generation_cohort(self, generation: int) -> List[GenealogyNode]:
        return [n for n in self._nodes.values() if n.generation == generation]

    def best_in_family(self, family: str) -> Optional[GenealogyNode]:
        members = self.family_members(family)
        if not members:
            return None
        return max(members, key=lambda n: n.birth_sharpe)

    def all_nodes(self) -> List[GenealogyNode]:
        return list(self._nodes.values())

    def summary(self) -> Dict[str, Any]:
        nodes = self.all_nodes()
        return {
            "total_strategies":  len(nodes),
            "seed_strategies":   len(self.seed_nodes()),
            "families":          list(self._families.keys()),
            "max_generation":    max((n.generation for n in nodes), default=0),
            "live":              sum(1 for n in nodes if n.status == "live"),
            "retired":           sum(1 for n in nodes if n.status == "retired"),
        }


# ---------------------------------------------------------------------------
# StrategyGenealogy — persistent façade
# ---------------------------------------------------------------------------

_NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class StrategyGenealogy:
    """
    Persistent strategy genealogy tracker.

    Usage
    -----
        genealogy = StrategyGenealogy(root="data/genealogy")

        # Register seed strategy
        genealogy.register(GenealogyNode(
            strategy_id  = "ema_trend_001",
            family       = "ema_trend",
            mutation_type = "seed",
            birth_sharpe  = 1.20,
            birth_regime  = "trending",
        ))

        # Register a mutated child
        genealogy.register(GenealogyNode(
            strategy_id     = "ema_trend_015",
            parent_id       = "ema_trend_011",
            family          = "ema_trend",
            generation      = 4,
            mutation_type   = "mutation",
            mutation_ops    = ["tweak_fast_period", "add_atr_filter"],
            parameter_delta = {"fast": 10, "slow": 30},
            birth_sharpe    = 1.94,
        ))

        # Get full ancestor chain
        ancestors = genealogy.ancestors("ema_trend_015")

        # Retire an entire subtree
        genealogy.retire_subtree("ema_trend_001", reason="seed bias discovered")
    """

    _NODES_DIR = "nodes"
    _LOG_FILE  = "genealogy_log.jsonl"

    def __init__(
        self,
        root:   str = "data/genealogy",
        config: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        if config and isinstance(config, dict):
            root = config.get("GENEALOGY_ROOT", root)

        self._root  = Path(root)
        self._nodes_dir = self._root / self._NODES_DIR
        self._log   = self._root / self._LOG_FILE
        self._tree  = GenealogyTree()
        self._lock  = threading.RLock()

        self._root.mkdir(parents=True, exist_ok=True)
        self._nodes_dir.mkdir(exist_ok=True)
        self._rebuild()

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def register(self, node: GenealogyNode) -> GenealogyNode:
        """Persist a node (new or updated)."""
        with self._lock:
            if not node.created_at:
                node.created_at = _NOW()
            # Auto-compute generation from parent if not set
            if node.generation == 0 and node.parent_id:
                parent = self._tree.get(node.parent_id)
                if parent:
                    node.generation = parent.generation + 1
            self._tree.add(node)
            self._write_node(node)
            self._append_log(node)
            return node

    def register_mutation(
        self,
        child_id:        str,
        parent_id:       str,
        family:          str,
        mutation_ops:    Optional[List[str]] = None,
        parameter_delta: Optional[Dict]      = None,
        birth_sharpe:    float               = 0.0,
        birth_drawdown:  float               = 0.0,
        birth_regime:    str                 = "all",
        tags:            Optional[List[str]] = None,
    ) -> GenealogyNode:
        """Convenience: register a single-parent mutation child."""
        parent = self._tree.get(parent_id)
        gen    = (parent.generation + 1) if parent else 1
        return self.register(GenealogyNode(
            strategy_id     = child_id,
            parent_id       = parent_id,
            family          = family,
            generation      = gen,
            mutation_type   = "mutation",
            mutation_ops    = mutation_ops or [],
            parameter_delta = parameter_delta or {},
            birth_sharpe    = birth_sharpe,
            birth_drawdown  = birth_drawdown,
            birth_regime    = birth_regime,
            tags            = tags or [],
        ))

    def register_crossover(
        self,
        child_id:        str,
        parent_a_id:     str,
        parent_b_id:     str,
        family:          str,
        birth_sharpe:    float = 0.0,
        birth_drawdown:  float = 0.0,
        birth_regime:    str   = "all",
    ) -> GenealogyNode:
        """Convenience: register a crossover child with two parents."""
        pa    = self._tree.get(parent_a_id)
        pb    = self._tree.get(parent_b_id)
        gen_a = (pa.generation + 1) if pa else 1
        gen_b = (pb.generation + 1) if pb else 1
        return self.register(GenealogyNode(
            strategy_id    = child_id,
            parent_id      = parent_a_id,
            parent_ids     = [parent_a_id, parent_b_id],
            family         = family,
            generation     = max(gen_a, gen_b),
            mutation_type  = "crossover",
            birth_sharpe   = birth_sharpe,
            birth_drawdown = birth_drawdown,
            birth_regime   = birth_regime,
        ))

    def update_status(self, strategy_id: str, status: str) -> Optional[GenealogyNode]:
        with self._lock:
            node = self._tree.get(strategy_id)
            if node is None:
                return None
            node.status = status
            if status == "retired" and not node.retired_at:
                node.retired_at = _NOW()
            return self.register(node)

    def retire_subtree(self, root_id: str, reason: str = "") -> List[str]:
        """
        Retire a strategy and all its descendants.
        Returns list of retired strategy_ids.
        """
        with self._lock:
            targets = [root_id] + [d.strategy_id for d in self._tree.descendants(root_id)]
            retired = []
            for sid in targets:
                node = self._tree.get(sid)
                if node and node.status != "retired":
                    node.status       = "retired"
                    node.retired_at   = _NOW()
                    node.retire_reason = reason
                    self.register(node)
                    retired.append(sid)
            return retired

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get(self, strategy_id: str) -> Optional[GenealogyNode]:
        return self._tree.get(strategy_id)

    def ancestors(self, strategy_id: str) -> List[GenealogyNode]:
        return self._tree.ancestors(strategy_id)

    def descendants(self, strategy_id: str) -> List[GenealogyNode]:
        return self._tree.descendants(strategy_id)

    def lineage_path(self, strategy_id: str) -> List[GenealogyNode]:
        return self._tree.lineage_path(strategy_id)

    def family_members(self, family: str) -> List[GenealogyNode]:
        return self._tree.family_members(family)

    def generation_cohort(self, generation: int) -> List[GenealogyNode]:
        return self._tree.generation_cohort(generation)

    def summary(self) -> Dict[str, Any]:
        return self._tree.summary()

    def lineage_report(self, strategy_id: str) -> Dict[str, Any]:
        """Human-readable lineage report for one strategy."""
        node = self._tree.get(strategy_id)
        if node is None:
            return {"error": f"strategy {strategy_id!r} not found"}
        path = self._tree.lineage_path(strategy_id)
        return {
            "strategy_id":   strategy_id,
            "family":        node.family,
            "generation":    node.generation,
            "mutation_type": node.mutation_type,
            "birth_sharpe":  node.birth_sharpe,
            "lineage_depth": len(path),
            "lineage": [
                {
                    "strategy_id":  n.strategy_id,
                    "generation":   n.generation,
                    "mutation_type": n.mutation_type,
                    "mutation_ops": n.mutation_ops,
                    "birth_sharpe": n.birth_sharpe,
                }
                for n in path
            ],
            "descendants_count": len(self._tree.descendants(strategy_id)),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_node(self, node: GenealogyNode) -> None:
        path = self._nodes_dir / f"{node.strategy_id}.json"
        tmp  = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(node.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)

    def _append_log(self, node: GenealogyNode) -> None:
        line = json.dumps({
            "strategy_id":  node.strategy_id,
            "parent_id":    node.parent_id,
            "generation":   node.generation,
            "family":       node.family,
            "mutation_type": node.mutation_type,
            "birth_sharpe": node.birth_sharpe,
            "status":       node.status,
            "ts":           _NOW(),
        })
        with open(self._log, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _rebuild(self) -> None:
        if not self._nodes_dir.exists():
            return
        for path in sorted(self._nodes_dir.glob("*.json")):
            try:
                d    = json.loads(path.read_text(encoding="utf-8"))
                node = GenealogyNode.from_dict(d)
                self._tree.add(node)
            except Exception:
                pass
