"""
Recursive Intelligence Engine for Quant Ecosystem 3.0

Meta-layer that monitors SelfAwarenessEngine decisions and adjusts its rules.
External layer that maintains safety and reversibility.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class RecursiveEngine:
    """
    Recursive AI that monitors and improves the SelfAwarenessEngine.
    Evaluates decision effectiveness and adjusts meta-rules safely.
    """

    def __init__(self):
        self.history = []
        self.rule_adjustments = []
        self.observation_interval = 20  # cycles between recursive evaluations
        self.cycle_count = 0
        self.last_adjustment_cycle = 0
        self.min_cycles_between_adjustments = 10  # safety: no adjustments too close together

    def observe(self, issues: List[str], actions: List[str], performance: float) -> None:
        """
        Record SelfAwarenessEngine decisions and their outcomes.

        Args:
            issues: Issues detected by SelfAwarenessEngine
            actions: Actions taken by SelfAwarenessEngine
            performance: Resulting performance metric (avg_win)
        """
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self.cycle_count,
            "issues": issues.copy(),
            "actions": actions.copy(),
            "performance": float(performance),
            "issues_count": len(issues),
            "actions_count": len(actions),
        }

        self.history.append(record)
        self.cycle_count += 1

        # Keep only last 20 observations
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def evaluate(self) -> Optional[str]:
        """
        Evaluate effectiveness of recent SelfAwarenessEngine decisions.

        Returns:
            "EFFECTIVE", "INEFFECTIVE", or None if insufficient data
        """
        if len(self.history) < 5:
            return None

        # Analyze last 5 observations
        recent = self.history[-5:]

        # Calculate performance trend
        performances = [r["performance"] for r in recent]
        avg_performance = sum(performances) / len(performances)

        # Check if actions led to improvement
        # Simple heuristic: positive average performance after actions
        actions_taken = sum(r["actions_count"] for r in recent)

        if actions_taken == 0:
            # No actions taken - neutral
            return "NEUTRAL"

        if avg_performance > 0:
            return "EFFECTIVE"
        else:
            return "INEFFECTIVE"

    def adjust_rules(self, self_awareness_engine, status: str) -> None:
        """
        Adjust SelfAwarenessEngine rules based on evaluation.

        Args:
            self_awareness_engine: The SelfAwarenessEngine to adjust
            status: "EFFECTIVE", "INEFFECTIVE", or "NEUTRAL"
        """
        # Safety check: don't adjust too frequently
        cycles_since_last_adjustment = self.cycle_count - self.last_adjustment_cycle
        if cycles_since_last_adjustment < self.min_cycles_between_adjustments:
            logger.info(f"Recursive AI: Skipping adjustment (too soon, {cycles_since_last_adjustment} cycles)")
            return

        adjustments_made = []

        if status == "INEFFECTIVE":
            # SelfAwarenessEngine is making poor decisions
            # Adjust sensitivity thresholds to be less aggressive

            # Make win rate threshold less sensitive (require worse performance to trigger)
            if hasattr(self_awareness_engine, 'win_rate_threshold'):
                old_value = self_awareness_engine.win_rate_threshold
                new_value = min(0.5, old_value * 1.02)  # Small increase (2%)
                self_awareness_engine.win_rate_threshold = new_value
                adjustments_made.append(f"win_rate_threshold: {old_value:.3f} -> {new_value:.3f}")

            # Make drawdown threshold more sensitive (trigger earlier)
            if hasattr(self_awareness_engine, 'drawdown_threshold'):
                old_value = self_awareness_engine.drawdown_threshold
                new_value = max(0.05, old_value * 0.98)  # Small decrease (2%)
                self_awareness_engine.drawdown_threshold = new_value
                adjustments_made.append(f"drawdown_threshold: {old_value:.3f} -> {new_value:.3f}")

            # Reduce observation frequency slightly
            if hasattr(self_awareness_engine, 'observation_interval'):
                old_value = self_awareness_engine.observation_interval
                new_value = min(15, old_value + 1)  # Increase interval by 1
                self_awareness_engine.observation_interval = new_value
                adjustments_made.append(f"observation_interval: {old_value} -> {new_value}")

        elif status == "EFFECTIVE":
            # SelfAwarenessEngine is making good decisions
            # Fine-tune thresholds for better sensitivity

            # Make win rate threshold more sensitive (trigger on better performance)
            if hasattr(self_awareness_engine, 'win_rate_threshold'):
                old_value = self_awareness_engine.win_rate_threshold
                new_value = max(0.3, old_value * 0.98)  # Small decrease (2%)
                self_awareness_engine.win_rate_threshold = new_value
                adjustments_made.append(f"win_rate_threshold: {old_value:.3f} -> {new_value:.3f}")

            # Make drawdown threshold less sensitive (allow more tolerance)
            if hasattr(self_awareness_engine, 'drawdown_threshold'):
                old_value = self_awareness_engine.drawdown_threshold
                new_value = min(0.2, old_value * 1.02)  # Small increase (2%)
                self_awareness_engine.drawdown_threshold = new_value
                adjustments_made.append(f"drawdown_threshold: {old_value:.3f} -> {new_value:.3f}")

        # Log adjustments
        if adjustments_made:
            adjustment_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "cycle": self.cycle_count,
                "status": status,
                "adjustments": adjustments_made,
                "reason": f"SelfAwarenessEngine evaluated as {status}"
            }
            self.rule_adjustments.append(adjustment_record)
            self.last_adjustment_cycle = self.cycle_count

            print("[RECURSIVE AI] Rule adjustments:")
            for adj in adjustments_made:
                print(f"  {adj}")

    def should_evaluate(self, cycle: int) -> bool:
        """Check if it's time to perform recursive evaluation."""
        return cycle % self.observation_interval == 0

    def get_status(self) -> Dict[str, Any]:
        """Get current recursive engine status."""
        return {
            "observations": len(self.history),
            "rule_adjustments": len(self.rule_adjustments),
            "last_evaluation": self.evaluate(),
            "cycle_count": self.cycle_count,
            "last_adjustment_cycle": self.last_adjustment_cycle
        }

    def get_recent_history(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get recent observation history."""
        return self.history[-n:] if self.history else []

    def get_recent_adjustments(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get recent rule adjustments."""
        return self.rule_adjustments[-n:] if self.rule_adjustments else []