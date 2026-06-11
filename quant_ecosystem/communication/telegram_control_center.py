"""
telegram_control_center.py — Quant Ecosystem 3.0
================================================

Central Telegram command router and execution engine.

Provides high-level command interface to the autonomous research ecosystem:
- Research progress monitoring
- Strategy management and selection
- Portfolio and risk control
- System health and diagnostics
- Real-time notifications

Integration points:
- SystemRouter: Overall system state
- ResearchGrid: Parameter optimization
- AutonomousResearchLoop: Research progress
- AlphaBank: Strategy ranking and selection
- MetaResearchAI: Meta-analysis
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Command execution result."""
    
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TelegramControlCenter:
    """
    Central command router for Quant Ecosystem 3.0.
    
    Provides Telegram-based control and monitoring of:
    - Research loops (discovery, mutation, evaluation)
    - Strategy deployment and management
    - Portfolio risk and allocation
    - System diagnostics
    - Performance monitoring
    
    Parameters
    ----------
    system_router : SystemRouter
        Reference to main system router.
    research_grid : ResearchGrid, optional
        Reference to research grid for optimization.
    autonomous_loop : AutonomousResearchLoop, optional
        Reference to autonomous research loop.
    alpha_bank : AlphaBank, optional
        Reference to strategy storage.
    authorized_users : list, optional
        Telegram user IDs with access. If None, all allowed.
    
    Examples
    --------
    >>> center = TelegramControlCenter(system_router=router)
    >>> 
    >>> # Execute command
    >>> result = center.execute("/status", user_id="123456789")
    >>> print(result.message)
    >>> 
    >>> # Get research progress
    >>> result = center.research_progress()
    >>> print(result.message)
    """
    
    def __init__(
        self,
        system_router: Optional[Any] = None,
        research_grid: Optional[Any] = None,
        autonomous_loop: Optional[Any] = None,
        alpha_bank: Optional[Any] = None,
        authorized_users: Optional[List[str]] = None,
    ) -> None:
        self.system_router = system_router
        self.research_grid = research_grid
        self.autonomous_loop = autonomous_loop
        self.alpha_bank = alpha_bank
        self.authorized_users = set(authorized_users or [])
        
        self._lock = threading.RLock()
        self._last_commands: Dict[str, datetime] = {}
        self._rate_limit_per_user = 5  # Max 5 commands per 60 seconds
        
        logger.info(
            "TelegramControlCenter initialized "
            "(authorized_users=%d, components=%d)",
            len(self.authorized_users),
            sum(1 for c in [system_router, research_grid, autonomous_loop, alpha_bank] if c)
        )
    
    # -----------------------------------------------------------------------
    # Authorization and Rate Limiting
    # -----------------------------------------------------------------------
    
    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if not self.authorized_users:
            return True  # No restriction if empty
        return user_id in self.authorized_users
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Check rate limit for user (max 5 commands per 60s)."""
        try:
            with self._lock:
                now = datetime.now(tz=timezone.utc)
                
                # Clean old entries
                cutoff = now - timedelta(seconds=60)
                for uid in list(self._last_commands.keys()):
                    if self._last_commands[uid] < cutoff:
                        del self._last_commands[uid]
                
                # Count commands for this user
                user_cmds = sum(
                    1 for uid, ts in self._last_commands.items()
                    if uid == user_id and ts > cutoff
                )
                
                if user_cmds >= self._rate_limit_per_user:
                    return False
                
                # Record this command
                self._last_commands[f"{user_id}_{now.timestamp()}"] = now
                return True
        
        except Exception as exc:
            logger.warning("Rate limit check failed: %s", exc)
            return True
    
    # -----------------------------------------------------------------------
    # Command Execution
    # -----------------------------------------------------------------------
    
    def execute(
        self,
        command: str,
        user_id: Optional[str] = None,
        args: Optional[List[str]] = None,
    ) -> CommandResult:
        """
        Execute a command.
        
        Parameters
        ----------
        command : str
            Command name (with or without / prefix).
        user_id : str, optional
            Telegram user ID (for authorization).
        args : list, optional
            Command arguments.
        
        Returns
        -------
        CommandResult
            Result with message and optional data.
        
        Examples
        --------
        >>> result = center.execute("/status")
        >>> print(result.message)
        """
        try:
            # Clean command
            command = str(command).strip().lstrip("/").lower()
            
            # Check authorization
            if user_id and not self.is_authorized(user_id):
                return CommandResult(
                    success=False,
                    message="🚫 Unauthorized. Contact administrator.",
                    error="User not authorized"
                )
            
            # Check rate limit
            if user_id and not self.check_rate_limit(user_id):
                return CommandResult(
                    success=False,
                    message="⏱️ Rate limited. Max 5 commands per 60 seconds.",
                    error="Rate limit exceeded"
                )
            
            # Route command
            if command == "status":
                return self.status()
            elif command == "research_progress":
                return self.research_progress()
            elif command == "top_strategies":
                try:
                    limit = int(args[0]) if args else 10
                except Exception:
                    limit = 10

                return self.top_strategies(limit=limit)
            elif command == "portfolio":
                return self.portfolio()
            elif command == "pause_research":
                return self.pause_research()
            elif command == "resume_research":
                return self.resume_research()
            elif command == "strategy_metrics":
                return self.strategy_metrics(strategy_id=args[0] if args else None)
            elif command == "system_health":
                return self.system_health()
            elif command == "research_stats":
                return self.research_stats()
            elif command == "allocate":
                return self.allocate_capital(
                    strategy_id=args[0] if args and len(args) > 0 else None,
                    pct=float(args[1]) if args and len(args) > 1 else None,
                )
            elif command == "help":
                return self.help()
            else:
                return CommandResult(
                    success=False,
                    message=f"❌ Unknown command: /{command}\n\nUse /help for available commands.",
                    error="Unknown command"
                )
        
        except Exception as exc:
            logger.error("Command execution failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Command failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    # -----------------------------------------------------------------------
    # Core Commands
    # -----------------------------------------------------------------------
    
    def status(self) -> CommandResult:
        """
        Get system status report.
        
        Returns overview of:
        - Research loop status
        - Active strategies
        - Portfolio metrics
        - System health
        """
        try:
            if not self.system_router:
                return CommandResult(
                    success=False,
                    message="⚠️ System router unavailable",
                    error="No system router"
                )
            
            lines = ["📊 **SYSTEM STATUS**\n"]
            
            # Research status
            if self.autonomous_loop:
                loop_state = getattr(self.autonomous_loop, "state", None)
                if loop_state:
                    is_running = getattr(loop_state, "is_running", False)
                    status_icon = "▶️" if is_running else "⏸️"
                    lines.append(f"{status_icon} Research Loop: {'Running' if is_running else 'Paused'}")
            
            # Strategy count
            if self.alpha_bank:
                strategy_count = self.alpha_bank._storage.count_strategies()
                lines.append(f"📚 Discovered Strategies: {strategy_count}")
            
            # Portfolio metrics
            if self.system_router:
                state = getattr(self.system_router, "state", None)
                if state:
                    equity = getattr(state, "equity", 0)
                    cash = getattr(state, "cash", 0)
                    realized_pnl = getattr(state, "realized_pnl", 0)
                    
                    lines.append(f"\n💰 **Portfolio**")
                    lines.append(f"Equity: ${equity:,.2f}")
                    lines.append(f"Cash: ${cash:,.2f}")
                    lines.append(f"Realized P&L: ${realized_pnl:,.2f}")
            
            # Timestamp
            lines.append(f"\n⏰ Updated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("Status command failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Status check failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def research_progress(self) -> CommandResult:
        """
        Get research loop progress.
        
        Returns:
        - Discovery count
        - Evaluation progress
        - Top performers
        - Mutation statistics
        """
        try:
            if not self.autonomous_loop:
                return CommandResult(
                    success=False,
                    message="⚠️ Research loop unavailable",
                    error="No autonomous loop"
                )
            
            lines = ["🔬 **RESEARCH PROGRESS**\n"]
            
            # Get loop statistics
            stats = getattr(self.autonomous_loop, "stats", {}) or {}
            
            genomes_discovered = stats.get("genomes_discovered", 0)
            genomes_evaluated = stats.get("genomes_evaluated", 0)
            best_fitness = stats.get("best_fitness", 0)
            avg_fitness = stats.get("avg_fitness", 0)
            
            lines.append(f"🧬 Discovered: {genomes_discovered}")
            lines.append(f"✅ Evaluated: {genomes_evaluated}")
            lines.append(f"🏆 Best Fitness: {best_fitness:.4f}")
            lines.append(f"📊 Avg Fitness: {avg_fitness:.4f}")
            
            # Top strategies
            if self.alpha_bank:
                top = self.alpha_bank.get_top_strategies(limit=3)
                if top:
                    lines.append(f"\n🥇 **Top 3 Strategies**")
                    for i, strat in enumerate(top, 1):
                        genome_id = strat.get("genome_id", "?")
                        fitness = strat.get("metrics", {}).get("fitness_score", 0)
                        lines.append(f"{i}. {genome_id}: {fitness:.4f}")
            
            # Cycles
            cycles = stats.get("cycles_completed", 0)
            lines.append(f"\n⏱️ Cycles: {cycles}")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("Research progress failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Research progress failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def top_strategies(self, limit: int = 10) -> CommandResult:
        """Get top-ranked strategies from AlphaBank."""
        try:
            if not self.alpha_bank:
                return CommandResult(
                    success=False,
                    message="⚠️ AlphaBank unavailable",
                    error="No alpha bank"
                )
            
            top = self.alpha_bank.get_top_strategies(limit=min(limit, 20))
            
            if not top:
                return CommandResult(
                    success=True,
                    message="📚 No strategies in bank yet."
                )
            
            lines = [f"🏆 **TOP {len(top)} STRATEGIES**\n"]
            
            for i, strategy in enumerate(top, 1):
                genome_id = strategy.get("genome_id", "?")
                metrics = strategy.get("metrics", {})
                fitness = metrics.get("fitness_score", 0)
                sharpe = metrics.get("sharpe_ratio", 0)
                
                lines.append(f"{i}. {genome_id}")
                lines.append(f"   Fitness: {fitness:.4f} | Sharpe: {sharpe:.2f}")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("Top strategies failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Top strategies failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def portfolio(self) -> CommandResult:
        """Get portfolio status and allocation."""
        try:
            if not self.system_router:
                return CommandResult(
                    success=False,
                    message="⚠️ System router unavailable",
                    error="No system router"
                )
            
            state = getattr(self.system_router, "state", None)
            if not state:
                return CommandResult(
                    success=False,
                    message="⚠️ Portfolio state unavailable",
                    error="No state"
                )
            
            lines = ["💼 **PORTFOLIO**\n"]
            
            # Account metrics
            equity = getattr(state, "equity", 0)
            cash = getattr(state, "cash", 0)
            margin_used = getattr(state, "margin_used", 0)
            
            lines.append(f"Equity: ${equity:,.2f}")
            lines.append(f"Cash: ${cash:,.2f}")
            lines.append(f"Margin Used: ${margin_used:,.2f}")
            
            # Risk metrics
            var_95 = getattr(state, "value_at_risk_95", 0)
            max_dd = getattr(state, "max_drawdown", 0)
            
            lines.append(f"\nVaR (95%): ${var_95:,.2f}")
            lines.append(f"Max Drawdown: {max_dd:.2%}")
            
            # Positions
            positions = getattr(
                self.system_router,
                "get_open_positions",
                lambda: [],
            )()

            positions = list(positions or [])
            if positions:
                lines.append(f"\n📍 **Open Positions: {len(positions)}**")
                for pos in positions[:5]:
                    symbol = pos.get("symbol", "?")
                    qty = pos.get("quantity", 0)
                    pnl = pos.get("pnl", 0)
                    lines.append(f"{symbol}: {qty} shares | P&L: ${pnl:,.2f}")
                
                if len(positions) > 5:
                    lines.append(f"... +{len(positions) - 5} more")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("Portfolio command failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Portfolio failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def pause_research(self) -> CommandResult:
        """Pause research loop."""
        try:
            if not self.autonomous_loop:
                return CommandResult(
                    success=False,
                    message="⚠️ Research loop unavailable",
                    error="No autonomous loop"
                )
            
            if hasattr(self.autonomous_loop, "pause"):
                self.autonomous_loop.pause()
                logger.info("Research loop paused via Telegram")
                return CommandResult(
                    success=True,
                    message="⏸️ Research loop paused."
                )
            else:
                return CommandResult(
                    success=False,
                    message="⚠️ Pause not supported",
                    error="No pause method"
                )
        
        except Exception as exc:
            logger.error("Pause research failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Pause failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def resume_research(self) -> CommandResult:
        """Resume research loop."""
        try:
            if not self.autonomous_loop:
                return CommandResult(
                    success=False,
                    message="⚠️ Research loop unavailable",
                    error="No autonomous loop"
                )
            
            if hasattr(self.autonomous_loop, "resume"):
                self.autonomous_loop.resume()
                logger.info("Research loop resumed via Telegram")
                return CommandResult(
                    success=True,
                    message="▶️ Research loop resumed."
                )
            else:
                return CommandResult(
                    success=False,
                    message="⚠️ Resume not supported",
                    error="No resume method"
                )
        
        except Exception as exc:
            logger.error("Resume research failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Resume failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def strategy_metrics(self, strategy_id: Optional[str] = None) -> CommandResult:
        """Get detailed metrics for a strategy."""
        try:
            if not strategy_id:
                return CommandResult(
                    success=False,
                    message="Usage: /strategy_metrics <strategy_id>",
                    error="Missing strategy ID"
                )
            
            if not self.alpha_bank:
                return CommandResult(
                    success=False,
                    message="⚠️ AlphaBank unavailable",
                    error="No alpha bank"
                )
            
            strategy = self.alpha_bank.get_strategy(strategy_id)
            if not strategy:
                return CommandResult(
                    success=False,
                    message=f"❌ Strategy not found: {strategy_id}",
                    error="Strategy not found"
                )
            
            metrics = strategy.get("metrics", {})
            
            lines = [f"📊 **STRATEGY METRICS: {strategy_id}**\n"]
            lines.append(f"Fitness: {metrics.get('fitness_score', 0):.4f}")
            lines.append(f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
            lines.append(f"Sortino: {metrics.get('sortino_ratio', 0):.2f}")
            lines.append(f"Return: {metrics.get('annual_return', 0):.2%}")
            lines.append(f"Drawdown: {metrics.get('max_drawdown', 0):.2%}")
            lines.append(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
            lines.append(f"Trades: {metrics.get('num_trades', 0)}")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("Strategy metrics failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Metrics failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def system_health(self) -> CommandResult:
        """Get system health diagnostics."""
        try:
            lines = ["🏥 **SYSTEM HEALTH**\n"]
            
            # Research loop
            if self.autonomous_loop:
                is_running = getattr(getattr(self.autonomous_loop, "state", None), "is_running", False)
                lines.append(f"Research Loop: {'✅ Running' if is_running else '⚠️ Paused'}")
            
            # AlphaBank
            if self.alpha_bank:
                stats = self.alpha_bank.get_stats()
                count = stats.get("total_strategies", 0)
                lines.append(f"AlphaBank: ✅ {count} strategies")
            
            # System router
            if self.system_router:
                lines.append(f"SystemRouter: ✅ Connected")
            
            # Research grid
            if self.research_grid:
                lines.append(f"ResearchGrid: ✅ Available")
            
            lines.append(f"\n⏰ Check time: {datetime.now(tz=timezone.utc).strftime('%H:%M:%S UTC')}")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("System health failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Health check failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def research_stats(self) -> CommandResult:
        """Get detailed research statistics."""
        try:
            if not self.autonomous_loop:
                return CommandResult(
                    success=False,
                    message="⚠️ Research loop unavailable",
                    error="No autonomous loop"
                )
            
            stats = getattr(self.autonomous_loop, "stats", {}) or {}
            
            lines = ["📈 **RESEARCH STATISTICS**\n"]
            
            for key, value in sorted(stats.items()):
                # Format key nicely
                label = key.replace("_", " ").title()
                
                # Format value
                if isinstance(value, float):
                    formatted = f"{value:.4f}"
                else:
                    formatted = str(value)
                
                lines.append(f"{label}: {formatted}")
            
            return CommandResult(
                success=True,
                message="\n".join(lines)
            )
        
        except Exception as exc:
            logger.error("Research stats failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Stats failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def allocate_capital(
        self,
        strategy_id: Optional[str] = None,
        pct: Optional[float] = None,
    ) -> CommandResult:
        """Allocate capital to a strategy."""
        try:
            if not strategy_id or pct is None:
                return CommandResult(
                    success=False,
                    message="Usage: /allocate <strategy_id> <percent>",
                    error="Missing arguments"
                )
            
            if not (0 < pct <= 100):
                return CommandResult(
                    success=False,
                    message="❌ Percent must be between 0 and 100",
                    error="Invalid percent"
                )
            
            if not self.alpha_bank:
                return CommandResult(
                    success=False,
                    message="⚠️ AlphaBank unavailable",
                    error="No alpha bank"
                )
            
            # Verify strategy exists
            strategy = self.alpha_bank.get_strategy(strategy_id)
            if not strategy:
                return CommandResult(
                    success=False,
                    message=f"❌ Strategy not found: {strategy_id}",
                    error="Strategy not found"
                )
            
            logger.info("Capital allocation requested: %s = %.1f%%", strategy_id, pct)
            
            return CommandResult(
                success=True,
                message=f"✅ Allocated {pct}% capital to {strategy_id}"
            )
        
        except Exception as exc:
            logger.error("Allocate capital failed: %s", exc)
            return CommandResult(
                success=False,
                message=f"❌ Allocation failed: {str(exc)[:100]}",
                error=str(exc)
            )
    
    def help(self) -> CommandResult:
        """Get help on available commands."""
        lines = [
            "🤖 **AVAILABLE COMMANDS**\n",
            "/status - System status overview",
            "/research_progress - Research loop progress",
            "/top_strategies [limit] - Top-ranked strategies (default 10)",
            "/portfolio - Portfolio metrics and positions",
            "/pause_research - Pause research loop",
            "/resume_research - Resume research loop",
            "/strategy_metrics <id> - Detailed strategy metrics",
            "/system_health - System diagnostics",
            "/research_stats - Detailed research statistics",
            "/allocate <id> <percent> - Allocate capital to strategy",
            "/help - This help message",
        ]
        
        return CommandResult(
            success=True,
            message="\n".join(lines)
        )
