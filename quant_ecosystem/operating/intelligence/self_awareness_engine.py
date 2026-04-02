"""
Self-Awareness Engine for Quant Ecosystem 3.0

Observes system performance, diagnoses weaknesses, and suggests safe improvements.
External layer that only adjusts parameters, never modifies core logic.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SelfAwarenessEngine:
    """
    Self-aware system that observes, diagnoses, and safely adjusts parameters.
    Never modifies core logic - only parameter tuning.
    """

    def __init__(self):
        self.history = []
        self.insights = []
        self.adjustment_log = []
        self.observation_interval = 10  # cycles between observations
        self.cycle_count = 0

        # Adjustable thresholds for recursive optimization
        self.win_rate_threshold = 0.4  # Below this = LOW_WIN_RATE
        self.drawdown_threshold = 0.1  # Above this = HIGH_DRAWDOWN
        self.strategy_diversity_threshold = 2  # Below this = LOW_STRATEGY_DIVERSITY
        self.trading_activity_threshold = 5  # Below this = LOW_TRADING_ACTIVITY

    def observe(self, state: Dict[str, Any]) -> None:
        """
        Collect system state snapshot for analysis.

        Args:
            state: Dictionary containing system metrics
        """
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self.cycle_count,
            "win_rate": float(state.get("win_rate", 0.0) or 0.0),
            "avg_pnl": float(state.get("avg_pnl", 0.0) or 0.0),
            "drawdown": float(state.get("drawdown", 0.0) or 0.0),
            "active_strategies": int(state.get("active_strategies", 0) or 0),
            "total_trades": int(state.get("total_trades", 0) or 0),
            "volatility": float(state.get("volatility", 0.0) or 0.0),
        }

        self.history.append(snapshot)
        self.cycle_count += 1

        # Keep only last 100 observations
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def diagnose(self) -> List[str]:
        """
        Analyze recent performance and identify issues.

        Returns:
            List of diagnosed problem categories
        """
        if not self.history:
            return []

        # Analyze last 5 observations for trends
        recent = self.history[-5:] if len(self.history) >= 5 else self.history
        latest = self.history[-1]

        issues = []

        # Win rate analysis
        avg_win_rate = sum(obs["win_rate"] for obs in recent) / len(recent)
        if avg_win_rate < self.win_rate_threshold:
            issues.append("LOW_WIN_RATE")
        elif latest["win_rate"] < self.win_rate_threshold - 0.05:  # More strict for latest
            issues.append("DECLINING_WIN_RATE")

        # PnL analysis
        if latest["avg_pnl"] < 0:
            issues.append("NEGATIVE_PNL")
        elif latest["avg_pnl"] < -10:  # Assuming currency units
            issues.append("SEVERE_NEGATIVE_PNL")

        # Drawdown analysis
        if latest["drawdown"] > self.drawdown_threshold + 0.05:  # 5% above threshold = HIGH
            issues.append("HIGH_DRAWDOWN")
        elif latest["drawdown"] > self.drawdown_threshold:  # At threshold = ELEVATED
            issues.append("ELEVATED_DRAWDOWN")

        # Strategy diversity
        if latest["active_strategies"] < self.strategy_diversity_threshold:
            issues.append("LOW_STRATEGY_DIVERSITY")

        # Trading activity
        if latest["total_trades"] < self.trading_activity_threshold:
            issues.append("LOW_TRADING_ACTIVITY")

        # Market volatility response
        if latest["volatility"] > 0.05 and latest["win_rate"] < 0.3:
            issues.append("VOLATILITY_STRESS")

        return issues

    def suggest(self, issues: List[str]) -> List[str]:
        """
        Generate safe improvement suggestions based on diagnosed issues.

        Args:
            issues: List of problem categories

        Returns:
            List of suggested actions (parameter adjustments only)
        """
        actions = []

        for issue in issues:
            if issue == "LOW_WIN_RATE":
                actions.append("reduce_risk_exposure")
                actions.append("tighten_entry_conditions")

            elif issue == "DECLINING_WIN_RATE":
                actions.append("reduce_position_sizes")
                actions.append("increase_confidence_threshold")

            elif issue == "NEGATIVE_PNL":
                actions.append("reduce_max_trade_risk")
                actions.append("limit_daily_trades")

            elif issue == "SEVERE_NEGATIVE_PNL":
                actions.append("emergency_risk_reduction")
                actions.append("pause_new_positions")

            elif issue == "HIGH_DRAWDOWN":
                actions.append("implement_strict_stops")
                actions.append("reduce_overall_exposure")

            elif issue == "ELEVATED_DRAWDOWN":
                actions.append("moderate_risk_reduction")
                actions.append("increase_risk_checks")

            elif issue == "LOW_STRATEGY_DIVERSITY":
                actions.append("encourage_strategy_activation")
                # Note: Cannot directly activate strategies, only adjust parameters

            elif issue == "LOW_TRADING_ACTIVITY":
                actions.append("relax_entry_conditions")
                actions.append("reduce_minimum_confidence")

            elif issue == "VOLATILITY_STRESS":
                actions.append("increase_volatility_adjustment")
                actions.append("reduce_leverage")

        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for action in actions:
            if action not in seen:
                unique_actions.append(action)
                seen.add(action)

        return unique_actions

    def apply(self, router, actions: List[str]) -> None:
        """
        Apply safe parameter adjustments only. Never modify core logic.

        Args:
            router: System router with engines
            actions: List of actions to apply
        """
        applied_changes = []

        for action in actions:
            try:
                if action == "reduce_risk_exposure":
                    if hasattr(router, 'risk_engine') and hasattr(router.risk_engine, 'max_trade_risk'):
                        old_value = router.risk_engine.max_trade_risk
                        router.risk_engine.max_trade_risk *= 0.9
                        applied_changes.append(f"max_trade_risk: {old_value:.4f} -> {router.risk_engine.max_trade_risk:.4f}")

                elif action == "reduce_max_trade_risk":
                    if hasattr(router, 'risk_engine') and hasattr(router.risk_engine, 'max_trade_risk'):
                        old_value = router.risk_engine.max_trade_risk
                        router.risk_engine.max_trade_risk *= 0.8
                        applied_changes.append(f"max_trade_risk: {old_value:.4f} -> {router.risk_engine.max_trade_risk:.4f}")

                elif action == "emergency_risk_reduction":
                    if hasattr(router, 'risk_engine') and hasattr(router.risk_engine, 'max_trade_risk'):
                        old_value = router.risk_engine.max_trade_risk
                        router.risk_engine.max_trade_risk *= 0.5
                        applied_changes.append(f"EMERGENCY: max_trade_risk: {old_value:.4f} -> {router.risk_engine.max_trade_risk:.4f}")

                elif action == "reduce_position_sizes":
                    if hasattr(router, 'execution_router') and hasattr(router.execution_router, 'max_position'):
                        old_value = getattr(router.execution_router, 'max_position', 1.0)
                        new_value = old_value * 0.9
                        setattr(router.execution_router, 'max_position', new_value)
                        applied_changes.append(f"max_position: {old_value:.4f} -> {new_value:.4f}")

                elif action == "increase_confidence_threshold":
                    if hasattr(router, 'execution_router') and hasattr(router.execution_router, 'min_confidence'):
                        old_value = getattr(router.execution_router, 'min_confidence', 0.45)
                        new_value = min(0.8, old_value * 1.1)
                        setattr(router.execution_router, 'min_confidence', new_value)
                        applied_changes.append(f"min_confidence: {old_value:.4f} -> {new_value:.4f}")

                elif action == "limit_daily_trades":
                    if hasattr(router, 'execution_router') and hasattr(router.execution_router, 'max_daily_trades'):
                        old_value = getattr(router.execution_router, 'max_daily_trades', 100)
                        new_value = max(5, int(old_value * 0.7))
                        setattr(router.execution_router, 'max_daily_trades', new_value)
                        applied_changes.append(f"max_daily_trades: {old_value} -> {new_value}")

                elif action == "implement_strict_stops":
                    if hasattr(router, 'risk_engine') and hasattr(router.risk_engine, 'stop_loss_pct'):
                        old_value = getattr(router.risk_engine, 'stop_loss_pct', 0.05)
                        new_value = min(0.02, old_value * 0.8)
                        setattr(router.risk_engine, 'stop_loss_pct', new_value)
                        applied_changes.append(f"stop_loss_pct: {old_value:.4f} -> {new_value:.4f}")

                elif action == "reduce_overall_exposure":
                    if hasattr(router, 'portfolio_engine') and hasattr(router.portfolio_engine, 'max_exposure'):
                        old_value = getattr(router.portfolio_engine, 'max_exposure', 0.8)
                        new_value = max(0.3, old_value * 0.9)
                        setattr(router.portfolio_engine, 'max_exposure', new_value)
                        applied_changes.append(f"max_exposure: {old_value:.4f} -> {new_value:.4f}")

                elif action == "moderate_risk_reduction":
                    if hasattr(router, 'risk_engine') and hasattr(router.risk_engine, 'max_trade_risk'):
                        old_value = router.risk_engine.max_trade_risk
                        router.risk_engine.max_trade_risk *= 0.95
                        applied_changes.append(f"max_trade_risk: {old_value:.4f} -> {router.risk_engine.max_trade_risk:.4f}")

                elif action == "relax_entry_conditions":
                    if hasattr(router, 'execution_router') and hasattr(router.execution_router, 'min_confidence'):
                        old_value = getattr(router.execution_router, 'min_confidence', 0.45)
                        new_value = max(0.2, old_value * 0.9)
                        setattr(router.execution_router, 'min_confidence', new_value)
                        applied_changes.append(f"min_confidence: {old_value:.4f} -> {new_value:.4f}")

                elif action == "reduce_minimum_confidence":
                    if hasattr(router, 'execution_router') and hasattr(router.execution_router, 'min_confidence'):
                        old_value = getattr(router.execution_router, 'min_confidence', 0.45)
                        new_value = max(0.1, old_value * 0.8)
                        setattr(router.execution_router, 'min_confidence', new_value)
                        applied_changes.append(f"min_confidence: {old_value:.4f} -> {new_value:.4f}")

                elif action == "increase_volatility_adjustment":
                    if hasattr(router, 'risk_engine') and hasattr(router.risk_engine, 'volatility_multiplier'):
                        old_value = getattr(router.risk_engine, 'volatility_multiplier', 1.0)
                        new_value = old_value * 1.2
                        setattr(router.risk_engine, 'volatility_multiplier', new_value)
                        applied_changes.append(f"volatility_multiplier: {old_value:.4f} -> {new_value:.4f}")

                elif action == "reduce_leverage":
                    if hasattr(router, 'execution_router') and hasattr(router.execution_router, 'leverage'):
                        old_value = getattr(router.execution_router, 'leverage', 1.0)
                        new_value = max(0.5, old_value * 0.9)
                        setattr(router.execution_router, 'leverage', new_value)
                        applied_changes.append(f"leverage: {old_value:.4f} -> {new_value:.4f}")

                # Note: Cannot directly pause positions or activate strategies
                # These would require core logic changes, which we avoid

            except Exception as e:
                logger.warning(f"Failed to apply action '{action}': {e}")

        # Log all applied changes
        if applied_changes:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "cycle": self.cycle_count,
                "actions_applied": applied_changes
            }
            self.adjustment_log.append(log_entry)

            print("[SELF-AWARENESS] Applied adjustments:")
            for change in applied_changes:
                print(f"  {change}")

    def should_observe(self, cycle: int) -> bool:
        """Check if it's time to perform observation and adjustment."""
        return cycle % self.observation_interval == 0

    def get_status(self) -> Dict[str, Any]:
        """Get current self-awareness status."""
        return {
            "observations": len(self.history),
            "adjustments": len(self.adjustment_log),
            "last_issues": self.diagnose() if self.history else [],
            "cycle_count": self.cycle_count
        }