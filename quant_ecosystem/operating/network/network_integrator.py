"""
NetworkIntegrator: Bridges Digital Intelligence Network with MasterOrchestrator

Responsibilities:
- Integrate network communication into orchestration loop
- Broadcast local knowledge (insights, strategies, metrics)
- Consume external knowledge from peers
- Use network data to improve local decisions
- Validate and apply network suggestions safely

Design: External networking layer - does NOT modify core trading logic
Safety: Network data used as suggestions only, never overwrites local decisions
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class NetworkIntegrator:
    """
    Integrates network communication with MasterOrchestrator.
    
    Lifecycle:
    - Every N cycles (configurable), broadcast local insights
    - Every N cycles, consume external insights
    - Use external knowledge to inform (not dictate) local decisions
    """

    def __init__(self, node, network_manager, orchestrator):
        """
        Initialize network integrator.
        
        Args:
            node: This system's NetworkNode
            network_manager: NetworkManager instance
            orchestrator: MasterOrchestrator instance
        """
        self.node = node
        self.network_manager = network_manager
        self.orchestrator = orchestrator
        
        # Configuration
        self.broadcast_interval = 10  # Broadcast every N cycles
        self.consume_interval = 10    # Consume insights every N cycles
        self.last_broadcast_cycle = 0
        self.last_consume_cycle = 0
        
        # Track decisions influenced by network
        self.network_influenced_decisions = 0
        self.network_suggestions_considered = 0

        # Grid state reference
        self.global_state = self.network_manager.global_state

        # Load balancing threshold
        self.overload_threshold = 0.8

        logger.info(f"[INTEGRATOR] Network integration initialized for node {self.node.node_id}")

    def should_broadcast(self, cycle_id: int) -> bool:
        """Check if it's time to broadcast."""
        return cycle_id - self.last_broadcast_cycle >= self.broadcast_interval

    def should_consume(self, cycle_id: int) -> bool:
        """Check if it's time to consume insights."""
        return cycle_id - self.last_consume_cycle >= self.consume_interval

    def sync_global_state(self, category: str, items: List[Dict[str, Any]]) -> None:
        """Update shared global state from local node."""
        if category not in self.global_state:
            logger.warning(f"[INTEGRATOR] Unknown global state category {category}")
            return

        self.global_state[category].extend(items if isinstance(items, list) else [items])
        self.network_manager.register_global_state(category, items)
        logger.debug(f"[INTEGRATOR] Synced global_state[{category}] (+{len(items)})")

    def distribute_task(self, task: str, data: Dict[str, Any]) -> bool:
        """Request task support from other grid nodes if overloaded."""
        if not self.node.is_overloaded():
            return False

        request = {
            "task": task,
            "data": data,
            "source": self.node.node_id,
            "source_reputation": self.node.reputation_score,
            "timestamp": datetime.now().isoformat(),
        }

        return self.network_manager.request_task(self.node.node_id, request)

    def request_network_capital(self, amount: float, strategy: str, expected_return: float) -> Dict[str, Any]:
        """Post a capital demand in the economic layer for peer provider evaluation."""
        request = {
            "source": self.node.node_id,
            "type": "capital_request",
            "amount": amount,
            "strategy": strategy,
            "expected_return": expected_return,
            "source_reputation": self.node.reputation_score,
            "timestamp": datetime.now().isoformat(),
        }

        result = self.network_manager.route_capital_request(self.node.node_id, request)
        logger.info(f"[INTEGRATOR] Capital request returned: {result}")
        return result

    def issue_strategy_offer(self, strategy_name: str, value_score: float, price: float) -> Dict[str, Any]:
        """Broadcast a strategy offer to peers on the strategy market."""
        offer = self.node.publish_strategy_offer(strategy_name, value_score, price)
        return offer

    def competition_cycle(self, cycle_id: int) -> Dict[str, Any]:
        """Trigger economic competition flow in the network manager."""
        stats = self.network_manager.run_economic_competition_cycle(cycle_id)
        if stats.get("status") == "competition_cycle_executed":
            logger.info(f"[INTEGRATOR] Economic competition cycle {cycle_id}: {stats}")
        return stats

    def consensus_before_action(self, action: str, required_role: str, required_majority: int = 1) -> bool:
        """Hold a consensus vote before important decisions."""
        proposal = {
            "action": action,
            "required_role": required_role,
            "source": self.node.node_id,
        }
        return self.network_manager.consensus_vote(proposal, required=required_majority)

    def broadcast_research_insights(self, cycle_id: int, research_engine: Any) -> bool:
        """
        Broadcast research insights to all peers.
        
        Args:
            cycle_id: Current orchestrator cycle
            research_engine: ResearchEngine instance with validated insights
        
        Returns:
            True if broadcast successful
        """
        try:
            # Get top research insights
            knowledge = research_engine.export_knowledge()
            top_insights = knowledge.get("top_insights", [])

            if not top_insights:
                logger.debug(f"[INTEGRATOR] No research insights to broadcast at cycle {cycle_id}")
                return False

            # Create broadcast message
            message = {
                "type": "insight",
                "content": {
                    "insights": top_insights[:5],
                    "cycle": cycle_id,
                    "source_system": "research_engine",
                },
                "symbol": "GLOBAL",
                "confidence": knowledge.get("avg_score", 0.5),
            }

            # Broadcast
            sent = self.node.broadcast(message)
            logger.info(f"[INTEGRATOR] Cycle {cycle_id}: Broadcast {len(top_insights[:5])} research insights to {sent} peers")

            self.last_broadcast_cycle = cycle_id
            return sent > 0

        except Exception as e:
            logger.error(f"[INTEGRATOR] Failed to broadcast research insights: {e}")
            return False

    def broadcast_strategy_performance(self, cycle_id: int, evolution_engine: Any) -> bool:
        """
        Broadcast strategy performance metrics to peers.
        
        Args:
            cycle_id: Current orchestrator cycle
            evolution_engine: EvolutionEngine with strategy scores
        
        Returns:
            True if broadcast successful
        """
        try:
            # Get top strategies with scores
            top_strategies = evolution_engine.select_top(top_n=3)
            strategy_scores = evolution_engine.strategy_scores or {}

            if not top_strategies:
                logger.debug(f"[INTEGRATOR] No strategies to broadcast at cycle {cycle_id}")
                return False

            # Create message with performance data
            message = {
                "type": "strategy",
                "content": {
                    "strategies": top_strategies,
                    "scores": {s: strategy_scores.get(s, 0) for s in top_strategies},
                    "cycle": cycle_id,
                },
                "symbol": "GLOBAL",
                "confidence": 0.7,  # Strategy performance is fairly reliable
            }

            # Broadcast
            sent = self.node.broadcast(message)
            logger.info(f"[INTEGRATOR] Cycle {cycle_id}: Broadcast {len(top_strategies)} strategies to {sent} peers")

            self.last_broadcast_cycle = cycle_id
            return sent > 0

        except Exception as e:
            logger.error(f"[INTEGRATOR] Failed to broadcast strategy performance: {e}")
            return False

    def broadcast_performance_metrics(self, cycle_id: int, learning_engine: Any, router_state: Any) -> bool:
        """
        Broadcast performance metrics to peers.
        
        Args:
            cycle_id: Current orchestrator cycle
            learning_engine: LearningEngine with performance data
            router_state: Router state with equity info
        
        Returns:
            True if broadcast successful
        """
        try:
            # Get performance metrics
            stats = learning_engine.evaluate()
            
            message = {
                "type": "metric",
                "content": {
                    "win_rate": stats.get("win_rate", 0),
                    "avg_win": stats.get("avg_win", 0),
                    "count": stats.get("count", 0),
                    "cycle": cycle_id,
                    "equity": float(getattr(router_state, "equity", 100_000) or 100_000),
                },
                "symbol": "GLOBAL",
                "confidence": 0.6,
            }

            # Broadcast
            sent = self.node.broadcast(message)
            logger.debug(f"[INTEGRATOR] Cycle {cycle_id}: Broadcast performance metrics to {sent} peers")

            return sent > 0

        except Exception as e:
            logger.error(f"[INTEGRATOR] Failed to broadcast performance metrics: {e}")
            return False

    def consume_external_insights(self, cycle_id: int) -> Dict[str, Any]:
        """
        Consume and process external insights from peers.
        
        Args:
            cycle_id: Current orchestrator cycle
        
        Returns:
            Dictionary with actionable insights
        """
        try:
            # Get received insights
            insights = self.node.get_insights_by_type("insight", limit=10)
            strategies = self.node.get_insights_by_type("strategy", limit=5)
            metrics = self.node.get_insights_by_type("metric", limit=5)

            # Aggregate strategy consensus
            strategy_consensus = self.network_manager.get_strategy_consensus(limit=3)

            result = {
                "external_insights": insights,
                "external_strategies": strategies,
                "external_metrics": metrics,
                "strategy_consensus": strategy_consensus,
                "cycle": cycle_id,
            }

            if insights:
                logger.info(f"[INTEGRATOR] Cycle {cycle_id}: Consumed {len(insights)} external insights from peers")
            if strategies:
                logger.info(f"[INTEGRATOR] Cycle {cycle_id}: Consumed {len(strategies)} external strategies")

            self.network_suggestions_considered += 1
            self.last_consume_cycle = cycle_id

            # Persist to global shared state for grid
            if insights:
                self.sync_global_state("insights", [i["content"] for i in insights if "content" in i])
            if strategies:
                self.sync_global_state("strategies", [s["content"] for s in strategies if "content" in s])
            if metrics:
                self.sync_global_state("performance", [m["content"] for m in metrics if "content" in m])

            return result

        except Exception as e:
            logger.error(f"[INTEGRATOR] Failed to consume external insights: {e}")
            return {"external_insights": [], "external_strategies": [], "external_metrics": []}

    def validate_network_suggestion(self, suggestion: Dict[str, Any], local_data: Dict[str, Any]) -> bool:
        """
        Validate network suggestion against local data (safety measure).
        
        Args:
            suggestion: Suggestion from network
            local_data: Local system metrics for validation
        
        Returns:
            True if suggestion is reasonable
        """
        # Check reputation of source
        source_reputation = suggestion.get("source_reputation", 50)
        if source_reputation < 40:
            logger.debug(f"[INTEGRATOR] Rejected suggestion from low-reputation source ({source_reputation})")
            return False

        # Check confidence
        confidence = suggestion.get("confidence", 0.5)
        if confidence < 0.3:
            logger.debug(f"[INTEGRATOR] Rejected suggestion with low confidence ({confidence})")
            return False

        # For strategy suggestions, check against local win rate
        if suggestion.get("type") == "strategy":
            local_win_rate = local_data.get("win_rate", 0.5)
            # Only accept if source has similar or better performance
            source_win_rate = suggestion.get("content", {}).get("source_win_rate", 0.5)
            if source_win_rate < local_win_rate * 0.7:  # At least 70% of local performance
                logger.debug(f"[INTEGRATOR] Rejected strategy suggestion (source win_rate {source_win_rate} < local {local_win_rate})")
                return False

        return True

    def apply_network_insights_to_strategy(
        self,
        cycle_id: int,
        external_insights: List[Dict[str, Any]],
        strategy_scores: Dict[str, float],
        local_win_rate: float
    ) -> Dict[str, Any]:
        """
        Apply external insights to improve strategy selection (suggestions only).
        
        Args:
            cycle_id: Current orchestrator cycle
            external_insights: Insights from network
            strategy_scores: Local strategy scores
            local_win_rate: Local system win rate
        
        Returns:
            Enhanced strategy scores boosted by external validation
        """
        try:
            enhanced_scores = strategy_scores.copy()

            for insight in external_insights:
                if not self.validate_network_suggestion(insight, {"win_rate": local_win_rate}):
                    continue

                # Extract strategy from insight
                strategy_name = insight.get("content", {}).get("strategy")
                confidence = insight.get("confidence", 0.5)

                if strategy_name and strategy_name in enhanced_scores:
                    # Boost score by small amount based on external validation
                    boost = 0.1 * confidence  # 0-10% boost
                    original = enhanced_scores[strategy_name]
                    enhanced_scores[strategy_name] = original * (1 + boost)

                    logger.debug(f"[INTEGRATOR] Boosted {strategy_name}: {original:.3f} → {enhanced_scores[strategy_name]:.3f}")
                    self.network_influenced_decisions += 1

            return enhanced_scores

        except Exception as e:
            logger.error(f"[INTEGRATOR] Failed to apply network insights: {e}")
            return strategy_scores

    def apply_network_insights_to_portfolio(
        self,
        cycle_id: int,
        external_metrics: List[Dict[str, Any]],
        allocations: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Apply external performance metrics to improve portfolio allocation (suggestions only).
        
        Args:
            cycle_id: Current orchestrator cycle
            external_metrics: Metrics from network
            allocations: Local capital allocations
        
        Returns:
            Adjusted allocations informed by external data
        """
        try:
            adjusted_allocs = allocations.copy()

            # Look for consistently high-performing symbols
            symbol_performance = defaultdict(list)
            
            for metric in external_metrics:
                content = metric.get("content", {})
                win_rate = content.get("win_rate", 0.5)
                symbol = metric.get("symbol", "GLOBAL")
                confidence = metric.get("confidence", 0.5)
                
                if symbol and win_rate > 0.55:  # Good performance
                    symbol_performance[symbol].append({
                        "win_rate": win_rate,
                        "confidence": confidence,
                    })

            # Rebalance allocations for well-performing symbols
            for symbol, performances in symbol_performance.items():
                avg_performance = sum(p["win_rate"] for p in performances) / len(performances)
                avg_confidence = sum(p["confidence"] for p in performances) / len(performances)

                if avg_performance > 0.6 and avg_confidence > 0.6:
                    # Increase allocation to this symbol
                    if symbol in adjusted_allocs:
                        boost = adjusted_allocs[symbol] * 0.05 * avg_confidence
                        adjusted_allocs[symbol] = adjusted_allocs[symbol] + boost
                        logger.debug(f"[INTEGRATOR] Boosted allocation to {symbol} based on external metrics")
                        self.network_influenced_decisions += 1

            return adjusted_allocs

        except Exception as e:
            logger.error(f"[INTEGRATOR] Failed to apply metrics to portfolio: {e}")
            return allocations

    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get status of network integration.
        
        Returns:
            Integration metrics and activity
        """
        return {
            "node_id": self.node.node_id,
            "broadcast_interval": self.broadcast_interval,
            "consume_interval": self.consume_interval,
            "last_broadcast_cycle": self.last_broadcast_cycle,
            "last_consume_cycle": self.last_consume_cycle,
            "network_influenced_decisions": self.network_influenced_decisions,
            "network_suggestions_considered": self.network_suggestions_considered,
            "peers_connected": len(self.node.peers),
            "shared_memory_size": len(self.node.shared_memory),
        }


# Import defaultdict for portfolio adjustment
from collections import defaultdict
