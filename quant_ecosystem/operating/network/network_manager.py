"""
NetworkManager: Central coordination for the Digital Intelligence Network

Manages:
- Node lifecycle (creation, connection, disconnection)
- Data flow between nodes
- Network topology
- Shared knowledge aggregation
- Safety and validation

Design: External networking layer - does NOT modify core trading logic
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class NetworkManager:
    """
    Manages a network of Quant Ecosystem nodes.
    
    Responsibilities:
    - Create and connect nodes
    - Manage network topology
    - Aggregate and synthesize shared knowledge
    - Track network health
    - Facilitate node communication
    """

    def __init__(self, network_name: str = "QE_Network"):
        """
        Initialize network manager.
        
        Args:
            network_name: Name of this network
        """
        self.network_name = network_name
        self.nodes: Dict[str, Any] = {}  # node_id -> NetworkNode
        self.nodes_by_type: Dict[str, List[str]] = defaultdict(list)
        
        # Global AI grid shared state
        self.global_state = {
            "insights": [],
            "strategies": [],
            "allocations": [],
            "performance": []
        }

        self.roles = ["research", "strategy", "execution", "risk", "portfolio", "general"]

        # Network metrics
        self.created_at = datetime.now()
        self.message_count = 0
        self.total_broadcasts = 0
        
        logger.info(f"[NETWORK_MGR] Network '{network_name}' initialized")

    def create_node(self, node_id: str, node_type: str = "general") -> Any:
        """
        Create a new network node.
        
        Args:
            node_id: Unique node identifier
            node_type: Type of node
        
        Returns:
            Created NetworkNode instance
        """
        from quant_ecosystem.operating.network.network_node import NetworkNode
        
        if node_id in self.nodes:
            logger.warning(f"[NETWORK_MGR] Node {node_id} already exists, returning existing")
            return self.nodes[node_id]

        node = NetworkNode(node_id, node_type)
        self.nodes[node_id] = node
        self.nodes_by_type[node_type].append(node_id)
        
        logger.info(f"[NETWORK_MGR] Created node {node_id} (type: {node_type})")
        return node

    def get_nodes_by_role(self, role: str) -> List[Any]:
        """Return nodes assigned to a role."""
        node_ids = self.nodes_by_type.get(role, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def register_global_state(self, category: str, items: List[Dict[str, Any]]) -> None:
        """
        Write data into the shared global state.
        """
        if category not in self.global_state:
            logger.warning(f"[NETWORK_MGR] Unknown global state category {category}")
            return
        self.global_state[category].extend(items if isinstance(items, list) else [items])
        logger.debug(f"[NETWORK_MGR] Global state {category} updated with {len(items)} items")

    def get_global_state(self) -> Dict[str, Any]:
        """Get global shared AI grid state."""
        return self.global_state

    def request_task(self, source_node_id: str, task_request: Dict[str, Any]) -> bool:
        """Route task request to role-capable peers."""
        task_name = task_request.get("task")
        if not task_name:
            logger.warning("[NETWORK_MGR] task_request missing task")
            return False

        target_role = "general"
        if task_name in ["analyze", "insight", "backtest"]:
            target_role = "research"
        elif task_name in ["build_strategy", "evaluate", "rank"]:
            target_role = "strategy"
        elif task_name in ["execute", "order", "trade"]:
            target_role = "execution"
        elif task_name in ["validate", "exposure", "limit"]:
            target_role = "risk"
        elif task_name in ["allocate", "rebalance", "optimize"]:
            target_role = "portfolio"

        # Find capable peers first
        candidates = self.get_nodes_by_role(target_role)
        if not candidates:
            candidates = [node for node in self.nodes.values() if node.role == "general"]

        if not candidates:
            logger.warning("[NETWORK_MGR] No candidate nodes available for task request")
            return False

        # Round robin task assignment
        selected = min(candidates, key=lambda x: x.broadcast_count + x.receive_count)
        response = selected.respond_task(task_request)
        if response:
            source = self.nodes.get(source_node_id)
            if source:
                source.receive(response)
            logger.info(f"[NETWORK_MGR] Task '{task_name}' delegated to {selected.node_id}")
            return True
        return False

    def route_capital_request(self, source_node_id: str, capital_request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a capital request among peers as an internal capital market."""
        source_node = self.nodes.get(source_node_id)
        if not source_node:
            return {"status": "error", "reason": "source_node_not_found"}

        # Gather responses from peers
        responses = []
        for node in self.nodes.values():
            if node.node_id == source_node_id:
                continue
            response = node.evaluate_capital_request(capital_request)
            if response.get("approved"):
                responses.append((node, response))

        if not responses:
            return {"status": "rejected", "reason": "no_approve"}

        # Choose the top approving bidder by available equity, then lowest price split
        responses.sort(key=lambda item: (item[0].equity, -item[1].get("profit_split", 0.3)), reverse=True)
        chosen_provider, agreement = responses[0]

        # execute funding and record trade (target node receives funds)
        source_node.process_capital_allocation({
            "amount": agreement["amount"],
            "strategy": capital_request.get("strategy"),
            "expected_return": capital_request.get("expected_return"),
            "profit_split": agreement["profit_split"],
        }, from_node=chosen_provider)

        source_node.trades_funded.append({
            "from": chosen_provider.node_id,
            "amount": agreement["amount"],
            "strategy": capital_request.get("strategy"),
            "expected_return": capital_request.get("expected_return"),
            "profit_split": agreement["profit_split"],
            "timestamp": datetime.now().isoformat(),
        })

        # persist to global state
        self.register_global_state("allocations", [{
            "source": chosen_provider.node_id,
            "target": source_node_id,
            "amount": agreement["amount"],
            "strategy": capital_request.get("strategy"),
            "profit_split": agreement["profit_split"],
            "timestamp": datetime.now().isoformat(),
        }])

        return {"status": "approved", "provider": chosen_provider.node_id, "amount": agreement["amount"], "profit_split": agreement["profit_split"]}

    def run_economic_competition_cycle(self, cycle_id: int) -> Dict[str, Any]:
        """Rank nodes and reallocate capital every N cycles, with weak nodes losing influence."""
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.equity, reverse=True)
        total_equity = sum(n.equity for n in sorted_nodes) if sorted_nodes else 0

        if total_equity <= 0:
            return {"status": "empty_network"}

        # top 30% get extra capital from weakest 20% if possible
        top_count = max(1, int(len(sorted_nodes) * 0.3))
        weak_count = max(1, int(len(sorted_nodes) * 0.2))

        top_nodes = sorted_nodes[:top_count]
        weak_nodes = sorted_nodes[-weak_count:]

        allocation_total = 0
        for top in top_nodes:
            bonus = min(top.equity * 0.05, top.cash * 0.2)
            top.cash += bonus
            top.equity += bonus
            allocation_total += bonus

        # reduce weak node influence
        for weak in weak_nodes:
            weak.apply_downward_pressure(factor=0.05)

        # update performance tracking and reputation
        for node in self.nodes.values():
            if node.performance_history:
                recent_pnl = node.performance_history[-1]["pnl"]
                node.update_reputation_for_pnl(recent_pnl)

        self.register_global_state("performance", [{"cycle": cycle_id, "total_equity": total_equity, "allocation_total": allocation_total}])

        return {
            "status": "competition_cycle_executed",
            "cycle": cycle_id,
            "top_nodes": [n.node_id for n in top_nodes],
            "weak_nodes": [n.node_id for n in weak_nodes],
            "total_equity": total_equity,
            "allocated_bonus": allocation_total,
        }

    def handle_node_failure(self, failed_node_id: str) -> Optional[Any]:
        """
        Reassign role and rewire peers if a node goes down.
        """
        failed = self.nodes.pop(failed_node_id, None)
        if not failed:
            return None

        if failed.role in self.nodes_by_type:
            self.nodes_by_type[failed.role] = [nid for nid in self.nodes_by_type[failed.role] if nid != failed_node_id]

        # Reassign role candidate
        possible = [n for n in self.nodes.values() if n.role == "general"]
        if not possible:
            logger.warning(f"[NETWORK_MGR] No general nodes available to assume role {failed.role}")
            return None

        chosen = min(possible, key=lambda x: x.broadcast_count + x.receive_count)
        chosen.set_role(failed.role)
        self.nodes_by_type[failed.role].append(chosen.node_id)

        logger.info(f"[NETWORK_MGR] Reassigned role {failed.role} from failed node {failed_node_id} to {chosen.node_id}")
        return chosen

    def consensus_vote(self, proposal: Dict[str, Any], required: int = 1) -> bool:
        """
        Conduct source voting among nodes before major action.
        """
        votes_yes = 0
        votes_no = 0
        for node in self.nodes.values():
            # Simple heuristic: prefer in-role nodes
            if node.role == proposal.get("required_role") or node.role == "general":
                if node.reputation_score >= 50:
                    votes_yes += 1
                else:
                    votes_no += 1
            else:
                votes_no += 1

        total = votes_yes + votes_no
        if total == 0:
            return False

        consensus = votes_yes >= max(required, (total // 2 + 1))
        logger.info(f"[NETWORK_MGR] Consensus vote for {proposal.get('action')} => yes: {votes_yes} no: {votes_no} => {consensus}")
        return consensus

    def connect_nodes(self, node_id1: str, node_id2: str, bidirectional: bool = True) -> bool:
        """
        Connect two nodes.
        
        Args:
            node_id1: First node
            node_id2: Second node
            bidirectional: If True, connection is two-way
        
        Returns:
            True if connection successful
        """
        if node_id1 not in self.nodes or node_id2 not in self.nodes:
            logger.error(f"[NETWORK_MGR] Cannot connect: nodes {node_id1} or {node_id2} not found")
            return False

        node1 = self.nodes[node_id1]
        node2 = self.nodes[node_id2]

        node1.add_peer(node2)
        
        if bidirectional:
            node2.add_peer(node1)

        logger.info(f"[NETWORK_MGR] Connected {node_id1} ↔ {node_id2}")
        return True

    def connect_all_nodes(self) -> int:
        """
        Connect all nodes in full mesh topology.
        
        Returns:
            Number of connections created
        """
        node_ids = list(self.nodes.keys())
        connection_count = 0

        for i, node_id1 in enumerate(node_ids):
            for node_id2 in node_ids[i + 1:]:
                if self.connect_nodes(node_id1, node_id2):
                    connection_count += 1

        logger.info(f"[NETWORK_MGR] Full mesh topology: {connection_count} connections")
        return connection_count

    def connect_by_type(self, type1: str, type2: str) -> int:
        """
        Connect all nodes of one type to nodes of another type.
        
        Args:
            type1: First node type
            type2: Second node type
        
        Returns:
            Number of connections created
        """
        nodes_type1 = [self.nodes[nid] for nid in self.nodes_by_type.get(type1, [])]
        nodes_type2 = [self.nodes[nid] for nid in self.nodes_by_type.get(type2, [])]
        
        connection_count = 0
        for node1 in nodes_type1:
            for node2 in nodes_type2:
                node1.add_peer(node2)
                connection_count += 1

        logger.info(f"[NETWORK_MGR] Connected {type1} nodes to {type2} nodes: {connection_count} connections")
        return connection_count

    def broadcast_from_node(self, node_id: str, data: Dict[str, Any]) -> int:
        """
        Broadcast data from specific node.
        
        Args:
            node_id: Source node
            data: Data to broadcast
        
        Returns:
            Number of peers message reached
        """
        if node_id not in self.nodes:
            logger.error(f"[NETWORK_MGR] Node {node_id} not found")
            return 0

        node = self.nodes[node_id]
        sent = node.broadcast(data)
        self.total_broadcasts += 1
        self.message_count += sent

        return sent

    def aggregate_insights(self, insight_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Aggregate insights of specific type from all nodes.
        
        Args:
            insight_type: Type of insight ("insight", "strategy", "metric", "performance")
            limit: Maximum insights to return
        
        Returns:
            Top insights sorted by confidence, with source diversity
        """
        all_insights = []
        
        for node in self.nodes.values():
            insights = node.get_insights_by_type(insight_type, limit=1000)
            all_insights.extend(insights)

        # Sort by confidence
        all_insights.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        # Deduplicate by content + source
        seen = set()
        unique_insights = []
        
        for insight in all_insights:
            key = (str(insight.get("content", {})), insight.get("source"))
            if key not in seen:
                seen.add(key)
                unique_insights.append(insight)
                if len(unique_insights) >= limit:
                    break

        logger.debug(f"[NETWORK_MGR] Aggregated {len(unique_insights)} unique {insight_type}s from {len(self.nodes)} nodes")
        return unique_insights

    def get_strategy_consensus(self, limit: int = 3) -> Dict[str, Any]:
        """
        Get consensus strategy recommendations from all nodes.
        
        Args:
            limit: Top N strategies to aggregate
        
        Returns:
            Aggregated strategy recommendation with consensus scoring
        """
        strategy_votes = defaultdict(lambda: {"score": 0, "votes": 0, "sources": set()})

        for node in self.nodes.values():
            strategies = node.get_insights_by_type("strategy", limit=limit)
            
            for strategy in strategies:
                content = str(strategy.get("content", ""))
                confidence = strategy.get("confidence", 0.5)
                
                strategy_votes[content]["score"] += confidence
                strategy_votes[content]["votes"] += 1
                strategy_votes[content]["sources"].add(strategy.get("source"))

        # Calculate consensus score
        consensus = []
        for strategy, data in strategy_votes.items():
            consensus_score = data["score"] / data["votes"] if data["votes"] > 0 else 0
            consensus.append({
                "strategy": strategy,
                "consensus_score": consensus_score,
                "votes": data["votes"],
                "sources": list(data["sources"]),
                "avg_confidence": consensus_score,
            })

        # Sort by consensus score
        consensus.sort(key=lambda x: x["consensus_score"], reverse=True)

        result = {
            "consensus_strategies": consensus[:limit],
            "total_votes": sum(s["votes"] for s in consensus),
            "participating_nodes": len(self.nodes),
            "agreement_level": len(set(s["strategy"] for s in consensus[:limit])) / limit if consensus else 0,
        }

        logger.debug(f"[NETWORK_MGR] Strategy consensus: {len(consensus)} unique strategies, {result['total_votes']} votes")
        return result

    def get_network_topology(self) -> Dict[str, Any]:
        """
        Get network topology and connectivity info.
        
        Returns:
            Detailed topology information
        """
        topology = {
            "network_name": self.network_name,
            "total_nodes": len(self.nodes),
            "nodes_by_type": dict(self.nodes_by_type),
            "connections": [],
            "node_details": [],
        }

        # Collect connections
        seen_connections = set()
        for node_id, node in self.nodes.items():
            for peer in node.peers:
                connection = tuple(sorted([node_id, peer.node_id]))
                if connection not in seen_connections:
                    seen_connections.add(connection)
                    topology["connections"].append({
                        "node1": connection[0],
                        "node2": connection[1],
                    })

        # Collect node details
        for node_id, node in self.nodes.items():
            topology["node_details"].append({
                "node_id": node_id,
                "node_type": node.node_type,
                "peers": len(node.peers),
                "memory_size": len(node.shared_memory),
                "reputation": node.reputation_score,
            })

        topology["total_connections"] = len(topology["connections"])

        return topology

    def get_network_status(self) -> Dict[str, Any]:
        """
        Get overall network health and status.
        
        Returns:
            Network health metrics
        """
        node_statuses = [node.get_network_status() for node in self.nodes.values()]

        total_reputation = sum(ns.get("reputation_score", 100) for ns in node_statuses)
        avg_reputation = total_reputation / len(node_statuses) if node_statuses else 0

        total_memory = sum(ns.get("shared_memory_size", 0) for ns in node_statuses)
        total_broadcasts = sum(ns.get("broadcast_count", 0) for ns in node_statuses)
        total_receives = sum(ns.get("receive_count", 0) for ns in node_statuses)

        return {
            "network_name": self.network_name,
            "timestamp": datetime.now().isoformat(),
            "uptime_minutes": (datetime.now() - self.created_at).total_seconds() / 60,
            "total_nodes": len(self.nodes),
            "total_connections": len(self._count_connections()),
            "avg_reputation": round(avg_reputation, 2),
            "total_messages_shared": total_memory,
            "total_broadcasts": total_broadcasts,
            "total_receives": total_receives,
            "node_statuses": node_statuses,
        }

    def get_node(self, node_id: str) -> Optional[Any]:
        """
        Get node by ID.
        
        Args:
            node_id: Node identifier
        
        Returns:
            NetworkNode or None
        """
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> List[Any]:
        """
        Get all nodes of specific type.
        
        Args:
            node_type: Type of node
        
        Returns:
            List of NetworkNodes
        """
        return [self.nodes[nid] for nid in self.nodes_by_type.get(node_type, [])]

    def _count_connections(self) -> set:
        """Count unique connections in network."""
        connections = set()
        for node in self.nodes.values():
            for peer in node.peers:
                conn = tuple(sorted([node.node_id, peer.node_id]))
                connections.add(conn)
        return connections

    def __repr__(self) -> str:
        return f"NetworkManager(network='{self.network_name}', nodes={len(self.nodes)}, connections={len(self._count_connections())})"
