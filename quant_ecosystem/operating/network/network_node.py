"""
NetworkNode: Individual node in the Digital Intelligence Network

Each node represents a Quant Ecosystem instance capable of:
- Sharing research insights with peers
- Broadcasting strategy performance
- Receiving external knowledge
- Improving decisions using network data

Design: External networking layer - does NOT modify core trading logic
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class NetworkNode:
    """
    Represents a single Quant Ecosystem instance in the digital network.
    
    Responsibilities:
    - Maintain peer connections
    - Broadcast local knowledge
    - Receive external insights
    - Store shared memory with validation
    
    Safety: All network data is treated as suggestions only, validated before use
    """

    def __init__(self, node_id: str, node_type: str = "general", initial_capital: float = 100000.0):
        """
        Initialize network node.
        
        Args:
            node_id: Unique identifier for this node (e.g., "node_usdinr_001")
            node_type: Type of node - "general", "research", "execution", "portfolio"
            initial_capital: Starting capital allocated to this node
        """
        self.node_id = node_id
        self.node_type = node_type
        self.peers: List['NetworkNode'] = []
        self.shared_memory: List[Dict[str, Any]] = []
        self.max_memory_size = 1000

        # Grid role list
        self.role = node_type if node_type in ["research", "strategy", "execution", "risk", "portfolio"] else "general"

        # Shared global intelligence state for grid usage
        self.global_state = {
            "insights": [],
            "strategies": [],
            "allocations": [],
            "performance": []
        }

        # Task request/response history
        self.request_log: List[Dict[str, Any]] = []
        self.response_log: List[Dict[str, Any]] = []

        # Economic identity
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.cash = initial_capital
        self.trades_funded = []  # list of orders funded by this node
        self.performance_history: List[Dict[str, Any]] = []

        # Performance tracking
        self.broadcast_count = 0
        self.receive_count = 0
        self.last_broadcast = None
        self.last_receive = None
        
        # Network metadata
        self.created_at = datetime.now()
        self.reputation_score = 100  # 0-100, decreases on invalid data
        
        logger.info(f"[NETWORK] Node {self.node_id} ({self.node_type}) initialized")

    def add_peer(self, peer: 'NetworkNode') -> None:
        """
        Add a peer node to this node's network.
        
        Args:
            peer: Another NetworkNode to connect to
        """
        if peer not in self.peers and peer.node_id != self.node_id:
            self.peers.append(peer)
            logger.info(f"[NETWORK] Node {self.node_id} connected to peer {peer.node_id}")

    def remove_peer(self, peer_id: str) -> None:
        """
        Remove a peer node from the network.
        
        Args:
            peer_id: ID of peer to disconnect
        """
        self.peers = [p for p in self.peers if p.node_id != peer_id]
        logger.info(f"[NETWORK] Node {self.node_id} disconnected from peer {peer_id}")

    def broadcast(self, data: Dict[str, Any]) -> int:
        """
        Broadcast data to all connected peers.
        
        Args:
            data: Dictionary with keys:
                - type: "insight", "strategy", "metric", "performance"
                - content: The actual data
                - symbol: Trading symbol (optional)
                - confidence: 0-1 confidence score
        
        Returns:
            Number of peers data was sent to
        """
        if not self.peers:
            logger.debug(f"[NETWORK] Node {self.node_id} has no peers to broadcast to")
            return 0

        # Validate data format
        if "type" not in data or "content" not in data:
            logger.warning(f"[NETWORK] Node {self.node_id} invalid broadcast format: missing type/content")
            return 0

        # Create network message
        message = {
            "source": self.node_id,
            "source_type": self.node_type,
            "type": data.get("type"),
            "content": data.get("content"),
            "symbol": data.get("symbol", "GLOBAL"),
            "confidence": data.get("confidence", 0.5),
            "timestamp": datetime.now().isoformat(),
            "source_reputation": self.reputation_score,
        }

        # Send to all peers
        sent_count = 0
        for peer in self.peers:
            try:
                peer.receive(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"[NETWORK] Failed to send to peer {peer.node_id}: {e}")

        self.broadcast_count += 1
        self.last_broadcast = datetime.now()
        
        logger.debug(f"[NETWORK] Node {self.node_id} broadcast {data['type']} to {sent_count} peers")
        return sent_count

    def receive(self, message: Dict[str, Any]) -> bool:
        """
        Receive data from another node.
        
        Args:
            message: Network message from peer
        
        Returns:
            True if message was stored, False if rejected
        """
        # Validate message
        if not self._validate_message(message):
            logger.warning(f"[NETWORK] Node {self.node_id} rejected invalid message from {message.get('source')}")
            return False

        # Check reputation of source
        source_reputation = message.get("source_reputation", 50)
        if source_reputation < 30:
            logger.warning(f"[NETWORK] Node {self.node_id} rejected message from low-reputation source {message.get('source')}")
            return False

        # Store in shared memory
        self.shared_memory.append(message)
        
        # Maintain size limit (FIFO)
        if len(self.shared_memory) > self.max_memory_size:
            removed = self.shared_memory.pop(0)
            logger.debug(f"[NETWORK] Node {self.node_id} evicted old message {removed['type']}")

        self.receive_count += 1
        self.last_receive = datetime.now()
        
        logger.debug(f"[NETWORK] Node {self.node_id} received {message['type']} from {message['source']}")
        return True

    def get_insights_by_type(self, insight_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve received insights of specific type.
        
        Args:
            insight_type: "insight", "strategy", "metric", "performance"
            limit: Maximum number to return
        
        Returns:
            List of matching messages sorted by confidence
        """
        matching = [
            msg for msg in self.shared_memory
            if msg.get("type") == insight_type
        ]
        
        # Sort by confidence (descending)
        matching.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return matching[:limit]

    def get_insights_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve received insights for specific symbol.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number to return
        
        Returns:
            List of messages for that symbol
        """
        matching = [
            msg for msg in self.shared_memory
            if msg.get("symbol") == symbol or msg.get("symbol") == "GLOBAL"
        ]
        
        # Sort by recency (newest first)
        matching.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return matching[:limit]

    def get_top_insights(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get highest-confidence insights from all sources.
        
        Args:
            limit: Number of insights to return
        
        Returns:
            Top insights sorted by confidence
        """
        sorted_memory = sorted(
            self.shared_memory,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        
        return sorted_memory[:limit]

    def update_peer_reputation(self, peer_id: str, delta: int) -> None:
        """
        Update reputation score for a peer based on message quality.
        
        Args:
            peer_id: ID of peer node
            delta: Change in reputation (-5 to +5)
        """
        for peer in self.peers:
            if peer.node_id == peer_id:
                old_score = peer.reputation_score
                peer.reputation_score = max(0, min(100, peer.reputation_score + delta))
                logger.debug(f"[NETWORK] Updated {peer_id} reputation: {old_score} → {peer.reputation_score}")
                break

    def get_network_status(self) -> Dict[str, Any]:
        """
        Get status of this node's network.
        
        Returns:
            Status dictionary with connectivity and performance info
        """
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "role": self.role,
            "connected_peers": len(self.peers),
            "peer_ids": [p.node_id for p in self.peers],
            "shared_memory_size": len(self.shared_memory),
            "global_state_entries": {k: len(v) for k, v in self.global_state.items()},
            "broadcast_count": self.broadcast_count,
            "receive_count": self.receive_count,
            "reputation_score": self.reputation_score,
            "last_broadcast": self.last_broadcast.isoformat() if self.last_broadcast else None,
            "last_receive": self.last_receive.isoformat() if self.last_receive else None,
            "equity": self.equity,
            "cash": self.cash,
            "performance_history_len": len(self.performance_history),
            "uptime_minutes": (datetime.now() - self.created_at).total_seconds() / 60,
        }

    def record_performance(self, cycle_id: int, pnl: float) -> None:
        """Record and apply performance result for economic evolution."""
        self.equity += pnl
        self.cash += pnl
        self.performance_history.append({
            "cycle": cycle_id,
            "pnl": pnl,
            "equity": self.equity,
            "timestamp": datetime.now().isoformat(),
        })
        self.update_reputation_for_pnl(pnl)

    def update_reputation_for_pnl(self, pnl: float) -> None:
        """Adjust reputation based on profit / loss."""
        if pnl > 0:
            delta = min(5, int((pnl / max(self.initial_capital, 1)) * 100))
        else:
            delta = max(-5, int((pnl / max(self.initial_capital, 1)) * 100))

        old_rep = self.reputation_score
        self.reputation_score = max(0, min(100, self.reputation_score + delta))
        logger.debug(f"[NETWORK] Node {self.node_id} reputation {old_rep} -> {self.reputation_score} (pnl {pnl})")

    def can_fund_amount(self, amount: float) -> bool:
        """Check if node has enough available capital for backing another node."""
        return amount > 0 and self.cash >= amount * 0.1 and amount <= self.cash * 0.5

    def evaluate_capital_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate incoming capital request and respond with approval / rejection."""
        amount = float(request.get("amount", 0))
        expected_return = float(request.get("expected_return", 0.0))
        source_reputation = int(request.get("source_reputation", 50))
        source_node = request.get("source")

        if amount <= 0 or expected_return <= 0:
            return {
                "source": self.node_id,
                "type": "capital_response",
                "approved": False,
                "amount": 0,
                "profit_split": 0.0,
                "reason": "invalid_request",
                "timestamp": datetime.now().isoformat(),
            }

        # Prefer high reputation borrowers and high expected ROI
        if source_reputation < 40 or self.reputation_score < 30:
            return {
                "source": self.node_id,
                "type": "capital_response",
                "approved": False,
                "amount": 0,
                "profit_split": 0.0,
                "reason": "low_reputation",
                "timestamp": datetime.now().isoformat(),
            }

        if not self.can_fund_amount(amount):
            return {
                "source": self.node_id,
                "type": "capital_response",
                "approved": False,
                "amount": 0,
                "profit_split": 0.0,
                "reason": "insufficient_funds",
                "timestamp": datetime.now().isoformat(),
            }

        # Approve partial or full based on performance history
        avg_pnl = sum(item["pnl"] for item in self.performance_history[-10:]) / max(1, min(10, len(self.performance_history)))
        approval_amount = min(amount, self.cash * 0.4)

        # if this node has strong recent performance, be more aggressive
        if avg_pnl > 0:
            approval_amount = min(amount, self.cash * 0.6)

        profit_split = 0.3

        # Premium to low-perf sources via ratio
        if expected_return < 0.1:
            profit_split = 0.35

        response = {
            "source": self.node_id,
            "type": "capital_response",
            "approved": True,
            "amount": round(approval_amount, 2),
            "profit_split": profit_split,
            "reason": "approved",
            "timestamp": datetime.now().isoformat(),
            "source_reputation": self.reputation_score,
        }

        return response

    def process_capital_allocation(self, agreement: Dict[str, Any], from_node: 'NetworkNode') -> None:
        """Record capital agreement between nodes and apply allocation rules."""
        allocated = float(agreement.get("amount", 0))
        if allocated <= 0:
            return

        # Safety caps: no more than 30% of counterpart cash per single allocation
        allowed_amount = min(allocated, from_node.cash * 0.3, self.equity * 0.5)
        allocated_amount = max(0.0, allowed_amount)

        if allocated_amount <= 0:
            return

        from_node.cash -= allocated_amount
        self.cash += allocated_amount

        self.trades_funded.append({
            "from": from_node.node_id,
            "amount": allocated_amount,
            "cycle": datetime.now().isoformat(),
            "strategy": agreement.get("strategy"),
            "expected_return": agreement.get("expected_return"),
            "profit_split": agreement.get("profit_split", 0.3),
        })

    def settle_funding_outcome(self, funding_record: Dict[str, Any], realized_return: float) -> None:
        """Distribute profit/loss according to profit split and update state."""
        principal = float(funding_record.get("amount", 0))
        profit_split = float(funding_record.get("profit_split", 0.3))
        if principal <= 0:
            return

        profit = principal * realized_return
        profit_to_self = profit * (1 - profit_split)
        profit_to_funder = profit * profit_split

        self.cash += profit_to_self
        self.equity += profit_to_self

        funder_node_id = funding_record.get("from")
        funder = next((p for p in self.peers if p.node_id == funder_node_id), None)
        if funder:
            funder.cash += profit_to_funder
            funder.equity += profit_to_funder
            funder.record_performance(cycle_id=0, pnl=profit_to_funder)

        self.record_performance(cycle_id=0, pnl=profit_to_self)

    def publish_strategy_offer(self, strategy_name: str, value_score: float, price: float) -> Dict[str, Any]:
        """Publish strategy and pricing to peers via networked strategy market."""
        offer = {
            "source": self.node_id,
            "type": "strategy_offer",
            "strategy": strategy_name,
            "value_score": value_score,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "source_reputation": self.reputation_score,
            "confidence": min(1.0, max(0.0, value_score / 10)),
        }
        self.broadcast(offer)
        return offer

    def evaluate_strategy_offer(self, offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Decide whether to adopt an offered strategy based on value and price."""
        if offer.get("type") != "strategy_offer":
            return None

        if self.reputation_score < 30 or self.cash <= 0:
            return None

        value_score = float(offer.get("value_score", 0.0))
        price = float(offer.get("price", 0.0))

        # Accept good value for money and high reputation sources
        if offer.get("source_reputation", 0) < 40 or value_score < 0.5:
            return None

        max_affordable = self.cash * 0.2
        if price > max_affordable:
            return None

        # simulate purchase and adoption
        self.cash -= price
        self.equity -= price
        self.update_reputation_for_pnl(value_score * 10)

        return {
            "source": self.node_id,
            "type": "strategy_purchase",
            "strategy": offer.get("strategy"),
            "price": price,
            "value_score": value_score,
            "from": offer.get("source"),
            "timestamp": datetime.now().isoformat(),
        }

    def evaluate_new_investment_caps(self) -> float:
        """Return how much new external capital this node can safely obtain."""
        if self.equity <= 0:
            return 0.0
        return min(self.equity * 0.5, max(0.0, self.cash * 2))

    def apply_downward_pressure(self, factor: float = 0.05) -> None:
        """Reduce influence for weak nodes in competition loop."""
        if self.reputation_score < 40:
            adjustment = self.equity * factor
            self.equity = max(0, self.equity - adjustment)
            self.cash = max(0, self.cash - adjustment)
            logger.debug(f"[NETWORK] Node {self.node_id} influence reduced by {adjustment}")

    def set_role(self, role: str) -> None:
        """Assign a role to this node (research/strategy/execution/risk/portfolio)."""
        roles = ["research", "strategy", "execution", "risk", "portfolio", "general"]
        if role not in roles:
            raise ValueError(f"Invalid role {role}")
        self.role = role
        logger.info(f"[NETWORK] Node {self.node_id} role changed to {self.role}")

    def can_handle_task(self, task: str) -> bool:
        """Check if node’s role allows handling the task."""
        mapping = {
            "research": ["analyze", "insight", "backtest"],
            "strategy": ["build_strategy", "evaluate", "rank"],
            "execution": ["execute", "order", "trade"],
            "risk": ["validate", "exposure", "limit"],
            "portfolio": ["allocate", "rebalance", "optimize"],
            "general": ["analyze", "execute", "allocate", "validate", "evaluate"]
        }
        return task in mapping.get(self.role, [])

    def request_task(self, task: str, data: Dict[str, Any]) -> int:
        """Broadcast task request to peers in need of help."""
        request = {
            "source": self.node_id,
            "source_type": self.node_type,
            "type": "task_request",
            "task": task,
            "content": data,
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.8,
            "source_reputation": self.reputation_score,
        }

        self.request_log.append(request)
        sent = 0
        for peer in self.peers:
            try:
                peer.receive(request)
                sent += 1
            except Exception as e:
                logger.error(f"[NETWORK] Task request forward failed {peer.node_id}: {e}")
        return sent

    def respond_task(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """If node can handle requested task, respond with result placeholder."""
        task = request.get("task")
        if not task or not self.can_handle_task(task):
            return None

        response = {
            "source": self.node_id,
            "source_type": self.node_type,
            "type": "task_response",
            "task": task,
            "content": {"status": "accepted", "node": self.node_id},
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.7,
            "source_reputation": self.reputation_score,
        }
        self.response_log.append(response)
        return response

    def update_global_state(self, updates: Dict[str, Any]) -> None:
        """Append data to shared global state categories."""
        for key in ["insights", "strategies", "allocations", "performance"]:
            if key in updates:
                self.global_state[key].extend(updates[key] if isinstance(updates[key], list) else [updates[key]])

    def get_global_state(self) -> Dict[str, Any]:
        """Return current global shared intelligence state."""
        return self.global_state

    def is_overloaded(self) -> bool:
        """Simple overload check based on message rates."""
        return (self.broadcast_count + self.receive_count) > 200

    def clear_memory(self) -> int:
        """
        Clear all shared memory.
        
        Returns:
            Number of messages cleared
        """
        count = len(self.shared_memory)
        self.shared_memory = []
        logger.info(f"[NETWORK] Node {self.node_id} cleared {count} messages from memory")
        return count

    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate message format and content.
        
        Args:
            message: Message to validate
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["source", "type", "content", "timestamp"]
        
        # Check required fields
        for field in required_fields:
            if field not in message:
                logger.debug(f"[NETWORK] Message validation failed: missing {field}")
                return False

        # Check type is valid
        valid_types = ["insight", "strategy", "metric", "performance", "alert", "capital_request", "capital_response", "strategy_offer", "strategy_purchase", "task_request", "task_response"]
        if message.get("type") not in valid_types:
            logger.debug(f"[NETWORK] Message validation failed: invalid type {message.get('type')}")
            return False

        # Check confidence is in valid range
        confidence = message.get("confidence", 0.5)
        if not (0 <= confidence <= 1):
            logger.debug(f"[NETWORK] Message validation failed: confidence {confidence} out of range")
            return False

        # Check content is not empty
        if not message.get("content"):
            logger.debug(f"[NETWORK] Message validation failed: empty content")
            return False

        return True

    def __repr__(self) -> str:
        return f"NetworkNode(id={self.node_id}, type={self.node_type}, peers={len(self.peers)}, memory={len(self.shared_memory)})"
