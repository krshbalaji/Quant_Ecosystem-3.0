"""
AI Agents for Quant Ecosystem 3.0 Multi-Agent System

Each agent wraps an existing engine and communicates via shared context.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from quant_ecosystem.operating.agents.base_agent import Agent


class ResearchAgent(Agent):
    """Autonomous research hypothesis generation and validation."""

    def __init__(self, research_engine):
        super().__init__("Research")
        self.engine = research_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate and test market hypotheses.
        
        Reads: market data
        Writes: insights, knowledge_base
        """
        self.execution_count += 1
        
        try:
            market_data = context.get("market_data", {})
            
            if not market_data:
                return {}
            
            # Run research cycle
            report = self.engine.run_research_cycle(market_data)
            
            self.last_output = report
            
            # Add to context
            context["insights"] = self.engine.export_knowledge()
            context["latest_hypothesis"] = report["hypothesis"]
            context["latest_hypothesis_score"] = report["result_score"]
            
            self.log_execution(f"Hypothesis: {report['hypothesis'][:30]}... Score: {report['result_score']:.4f}")
            
            return context.get("insights", {})
            
        except Exception as e:
            self.log_error("Research cycle failed", e)
            return {}


class StrategyAgent(Agent):
    """Strategic analysis and meta-strategy management."""

    def __init__(self, evolution_engine):
        super().__init__("Strategy")
        self.engine = evolution_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select and rank strategies based on performance.
        
        Reads: insights, performance metrics
        Writes: active_strategies, strategy_rankings
        """
        self.execution_count += 1
        
        try:
            # Get top strategies
            top_strategies = self.engine.select_top(top_n=5)
            
            # Get strategy scores
            scores = self.engine.strategy_scores or {}
            
            self.last_output = {
                "top_strategies": top_strategies,
                "scores": scores,
            }
            
            # Update context
            context["active_strategies"] = top_strategies
            context["strategy_scores"] = scores
            
            self.log_execution(f"Top strategies: {top_strategies}")
            
            return self.last_output
            
        except Exception as e:
            self.log_error("Strategy selection failed", e)
            return {}


class PortfolioAgent(Agent):
    """Portfolio allocation and capital management."""

    def __init__(self, portfolio_engine):
        super().__init__("Portfolio")
        self.engine = portfolio_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Allocate capital across strategies and markets.
        
        Reads: strategy_scores, market data
        Writes: allocations, exposure
        """
        self.execution_count += 1
        
        try:
            strategy_scores = context.get("strategy_scores", {})
            market_intelligence = context.get("market_intelligence", {})
            
            if not strategy_scores:
                return {}
            
            # Allocate capital
            allocations = self.engine.allocate(strategy_scores, market_intelligence)
            
            # Get market exposure
            total_exposure = self.engine.get_total_exposure()
            
            self.last_output = {
                "allocations": allocations,
                "total_exposure": total_exposure,
            }
            
            # Update context
            context["allocations"] = allocations
            context["total_exposure"] = total_exposure
            
            self.log_execution(f"Exposure: {total_exposure:.0f} | Strategies: {len(allocations)}")
            
            return self.last_output
            
        except Exception as e:
            self.log_error("Portfolio allocation failed", e)
            return {}


class RiskAgent(Agent):
    """Risk management and position validation."""

    def __init__(self, risk_engine):
        super().__init__("Risk")
        self.engine = risk_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate exposure and enforce risk limits.
        
        Reads: allocations, market data
        Writes: risk_status, constraints
        """
        self.execution_count += 1
        
        try:
            total_exposure = context.get("total_exposure", 0.0)
            allocations = context.get("allocations", {})
            
            # Check risk constraints
            risk_status = {
                "exposure_check": total_exposure <= 0.5,  # 50% max
                "total_exposure": total_exposure,
                "allocation_count": len(allocations),
            }
            
            self.last_output = risk_status
            context["risk_status"] = risk_status
            
            if risk_status["exposure_check"]:
                self.log_execution("Risk limits OK")
            else:
                self.log_execution("⚠️ Exposure HIGH - reducing trades")
            
            return risk_status
            
        except Exception as e:
            self.log_error("Risk check failed", e)
            return {}


class ExecutionAgent(Agent):
    """Trade execution and order management."""

    def __init__(self, execution_router):
        super().__init__("Execution")
        self.router = execution_router

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute trades based on allocations.
        
        Reads: allocations, risk_status  
        Writes: executed_trades, execution_status
        """
        self.execution_count += 1
        
        try:
            risk_status = context.get("risk_status", {})
            
            # Safety check
            if not risk_status.get("exposure_check", False):
                self.log_execution("Skipped: Over-exposed")
                return {"executed": 0, "reason": "EXPOSURE_LIMIT"}
            
            # Placeholder for execution (actual execution happens in orchestrator)
            execution_status = {
                "ready": True,
                "reason": "Risk check passed",
            }
            
            self.last_output = execution_status
            context["execution_status"] = execution_status
            
            self.log_execution("Ready for execution")
            
            return execution_status
            
        except Exception as e:
            self.log_error("Execution check failed", e)
            return {}


class AwarenessAgent(Agent):
    """System self-awareness and performance monitoring."""

    def __init__(self, self_awareness_engine):
        super().__init__("Awareness")
        self.engine = self_awareness_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor and diagnose system performance.
        
        Reads: performance metrics
        Writes: issues, suggested_actions
        """
        self.execution_count += 1
        
        try:
            # Get performance data
            learning_stats = context.get("learning_stats", {})
            
            state = {
                "win_rate": learning_stats.get("win_rate", 0.0),
                "avg_pnl": learning_stats.get("avg_win", 0.0),
                "drawdown": context.get("drawdown", 0.0),
                "active_strategies": len(context.get("active_strategies", [])),
                "total_trades": context.get("total_trades", 0),
                "volatility": context.get("market_volatility", 0.0),
            }
            
            # Observe state
            self.engine.observe(state)
            
            # Diagnose issues
            issues = self.engine.diagnose()
            
            # Suggest actions
            actions = self.engine.suggest(issues)
            
            self.last_output = {
                "issues": issues,
                "actions": actions,
            }
            
            # Update context
            context["system_issues"] = issues
            context["suggested_actions"] = actions
            
            if issues:
                self.log_execution(f"Issues: {issues[:2]} | Actions: {len(actions)}")
            else:
                self.log_execution("System healthy")
            
            return self.last_output
            
        except Exception as e:
            self.log_error("Awareness check failed", e)
            return {}


class RecursiveAgent(Agent):
    """Meta-learning for system rule optimization."""

    def __init__(self, recursive_engine):
        super().__init__("Recursive")
        self.engine = recursive_engine

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate and improve system decisions.
        
        Reads: issues, actions, performance
        Writes: rule_adjustments, meta_status
        """
        self.execution_count += 1
        
        try:
            issues = context.get("system_issues", [])
            actions = context.get("suggested_actions", [])
            performance = context.get("learning_stats", {}).get("avg_win", 0.0)
            
            # Observe decisions
            self.engine.observe(issues, actions, performance)
            
            # Evaluate effectiveness
            status = self.engine.evaluate()
            
            self.last_output = {
                "evaluation_status": status,
                "rule_adjustments": len(self.engine.rule_adjustments),
            }
            
            context["recursive_status"] = status
            
            if status:
                self.log_execution(f"Status: {status}")
            else:
                self.log_execution("Insufficient data for evaluation")
            
            return self.last_output
            
        except Exception as e:
            self.log_error("Recursive evaluation failed", e)
            return {}
