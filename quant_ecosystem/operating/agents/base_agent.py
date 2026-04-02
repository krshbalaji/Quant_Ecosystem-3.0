"""
Base Agent for Quant Ecosystem 3.0 Multi-Agent System

All AI agents inherit from this base class.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Agent(ABC):
    """Base class for all ecosystem agents."""

    def __init__(self, name: str):
        self.name = name
        self.execution_count = 0
        self.last_output = None
        self.error_count = 0

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Any:
        """
        Execute agent logic with shared context.
        
        Args:
            context: Shared context dictionary with system state
            
        Returns:
            Agent output/results
        """
        pass

    def log_execution(self, message: str):
        """Log agent execution."""
        logger.info(f"[AGENT:{self.name}] {message}")

    def log_error(self, message: str, error: Exception = None):
        """Log agent errors."""
        self.error_count += 1
        if error:
            logger.error(f"[AGENT:{self.name}] {message}: {error}")
        else:
            logger.error(f"[AGENT:{self.name}] {message}")

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "name": self.name,
            "executions": self.execution_count,
            "errors": self.error_count,
            "has_output": self.last_output is not None,
        }
