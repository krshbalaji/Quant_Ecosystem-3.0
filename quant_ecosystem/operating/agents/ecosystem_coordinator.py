"""
Ecosystem Coordinator for Quant Ecosystem 3.0

Manages multi-agent collaboration and shared context.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class EcosystemCoordinator:
    """
    Coordinates multiple AI agents through a shared context.
    
    Implements message passing and execution ordering for:
    - Research Agent: hypothesis generation
    - Strategy Agent: strategy selection  
    - Portfolio Agent: capital allocation
    - Risk Agent: exposure validation
    - Execution Agent: trade execution
    - Awareness Agent: performance monitoring
    - Recursive Agent: system rule optimization
    """

    def __init__(self, agents: Dict[str, Any]):
        """
        Initialize coordinator with agents.
        
        Args:
            agents: Dictionary mapping agent names to agent instances
        """
        self.agents = agents
        self.cycle_count = 0
        self.execution_history = []

    def initialize_context(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize shared context with base market data.
        
        Args:
            base_data: Base context with market_data, intelligence, etc.
            
        Returns:
            Initialized context dictionary
        """
        context = {
            "cycle": self.cycle_count,
            "timestamp": None,
            # Market data
            "market_data": base_data.get("market_data", {}),
            "market_intelligence": base_data.get("market_intelligence", {}),
            "market_volatility": base_data.get("market_volatility", 0.0),
            # Insights
            "insights": {},
            "latest_hypothesis": None,
            "latest_hypothesis_score": 0.0,
            # Strategies
            "active_strategies": [],
            "strategy_scores": {},
            # Portfolio
            "allocations": {},
            "total_exposure": 0.0,
            # Risk
            "risk_status": {},
            # Performance
            "learning_stats": base_data.get("learning_stats", {}),
            "drawdown": base_data.get("drawdown", 0.0),
            "total_trades": base_data.get("total_trades", 0),
            # Execution
            "execution_status": {},
            # Self-awareness
            "system_issues": [],
            "suggested_actions": [],
            # Recursive learning
            "recursive_status": None,
        }
        
        return context

    def run_cycle(self, context: Dict[str, Any], apply_awareness_actions: bool = False) -> Dict[str, Any]:
        """
        Execute complete agent coordination cycle.
        
        Agent execution order:
        1. ResearchAgent → generate insights
        2. StrategyAgent → select strategies
        3. PortfolioAgent → allocate capital
        4. RiskAgent → validate exposure
        5. ExecutionAgent → check readiness
        6. AwarenessAgent → evaluate performance
        7. RecursiveAgent → optimize rules
        
        Args:
            context: Shared context
            apply_awareness_actions: Whether to apply awareness adjustments (optional)
            
        Returns:
            Updated context with all agent outputs
        """
        self.cycle_count += 1
        context["cycle"] = self.cycle_count

        execution_log = {
            "cycle": self.cycle_count,
            "agents_executed": [],
            "agent_outputs": {},
        }

        try:
            # 1. RESEARCH AGENT
            if "research" in self.agents:
                output = self.agents["research"].run(context)
                execution_log["agents_executed"].append("research")
                execution_log["agent_outputs"]["research"] = bool(output)

            # 2. STRATEGY AGENT
            if "strategy" in self.agents:
                output = self.agents["strategy"].run(context)
                execution_log["agents_executed"].append("strategy")
                execution_log["agent_outputs"]["strategy"] = bool(output)

            # 3. PORTFOLIO AGENT
            if "portfolio" in self.agents:
                output = self.agents["portfolio"].run(context)
                execution_log["agents_executed"].append("portfolio")
                execution_log["agent_outputs"]["portfolio"] = bool(output)

            # 4. RISK AGENT
            if "risk" in self.agents:
                output = self.agents["risk"].run(context)
                execution_log["agents_executed"].append("risk")
                execution_log["agent_outputs"]["risk"] = bool(output)

            # 5. EXECUTION AGENT
            if "execution" in self.agents:
                output = self.agents["execution"].run(context)
                execution_log["agents_executed"].append("execution")
                execution_log["agent_outputs"]["execution"] = bool(output)

            # 6. AWARENESS AGENT (optional adjustments)
            if "awareness" in self.agents:
                output = self.agents["awareness"].run(context)
                execution_log["agents_executed"].append("awareness")
                execution_log["agent_outputs"]["awareness"] = bool(output)
                
                # Apply adjustments if enabled
                if apply_awareness_actions and output:
                    actions = context.get("suggested_actions", [])
                    if actions and "router" in self.agents:
                        try:
                            self.agents["awareness"].engine.apply(
                                self.agents["router"],
                                actions
                            )
                        except Exception as e:
                            logger.warning(f"Failed to apply awareness actions: {e}")

            # 7. RECURSIVE AGENT (meta-learning)
            if "recursive" in self.agents:
                output = self.agents["recursive"].run(context)
                execution_log["agents_executed"].append("recursive")
                execution_log["agent_outputs"]["recursive"] = bool(output)

        except Exception as e:
            logger.error(f"Agent coordination cycle failed: {e}")

        self.execution_history.append(execution_log)
        
        # Keep only last 100 cycles
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

        return context

    def get_active_agents(self) -> List[str]:
        """Get list of active agent names."""
        return list(self.agents.keys())

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        status = {}
        for name, agent in self.agents.items():
            if hasattr(agent, 'get_status'):
                status[name] = agent.get_status()
            else:
                status[name] = {"type": "external", "name": name}
        
        return status

    def get_context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of current context state.
        
        Args:
            context: Shared context
            
        Returns:
            Summary of key context values
        """
        return {
            "cycle": context.get("cycle", 0),
            "active_strategies": len(context.get("active_strategies", [])),
            "total_exposure": context.get("total_exposure", 0.0),
            "system_issues": len(context.get("system_issues", [])),
            "risk_check": context.get("risk_status", {}).get("exposure_check", False),
            "execution_ready": context.get("execution_status", {}).get("ready", False),
        }

    def print_status(self, context: Dict[str, Any]):
        """Print ecosystem status to console."""
        print("[ECOSYSTEM COORDINATOR]")
        print(f"  Cycle: {context.get('cycle', 0)}")
        print(f"  Active agents: {len(self.agents)}")
        print(f"  Strategies active: {len(context.get('active_strategies', []))}")
        print(f"  Total exposure: {context.get('total_exposure', 0.0):.0f}")
        
        if context.get("system_issues"):
            print(f"  ⚠️  Issues: {', '.join(context.get('system_issues', [])[:2])}")
        else:
            print(f"  ✓ System healthy")
        
        # Agent summary
        agent_summary = []
        for name in self.get_active_agents():
            if name != "router":  # Skip non-agent components
                status = "OK"
                if name in self.agents and hasattr(self.agents[name], 'error_count'):
                    if self.agents[name].error_count > 0:
                        status = f"⚠️ {self.agents[name].error_count} errors"
                agent_summary.append(f"{name.upper()}:{status}")
        
        print(f"  Agents: {' | '.join(agent_summary)}")
