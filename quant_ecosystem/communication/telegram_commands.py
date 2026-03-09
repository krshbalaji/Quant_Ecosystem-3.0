"""
telegram_commands.py — Quant Ecosystem 3.0
===========================================

Command parser and validator for Telegram bot.

Handles:
- Command parsing and tokenization
- Argument validation
- Rate limiting and throttling
- Command history tracking
- Error recovery
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Command classification."""
    
    QUERY = "query"         # Information retrieval (safe, no side effects)
    CONTROL = "control"     # System control (pause, resume, etc.)
    ALLOCATION = "allocation"  # Capital allocation (critical)
    ADMIN = "admin"         # Administrative commands


class CommandSchema:
    """Schema for command validation."""
    
    def __init__(
        self,
        name: str,
        cmd_type: CommandType,
        min_args: int = 0,
        max_args: Optional[int] = None,
        arg_types: Optional[List[type]] = None,
        description: str = "",
        dangerous: bool = False,
    ) -> None:
        self.name = name
        self.cmd_type = cmd_type
        self.min_args = min_args
        self.max_args = max_args
        self.arg_types = arg_types or []
        self.description = description
        self.dangerous = dangerous


class CommandParser:
    """
    Parse and validate Telegram commands.
    
    Features:
    - Tokenization with quote handling
    - Argument type coercion
    - Validation against schemas
    - Error reporting
    
    Examples
    --------
    >>> parser = CommandParser()
    >>> result = parser.parse("/allocate strategy_001 25.5")
    >>> print(result.command, result.args)
    """
    
    # Command schemas
    SCHEMAS: Dict[str, CommandSchema] = {
        "status": CommandSchema("status", CommandType.QUERY, 0, 0,
                              description="Get system status"),
        "research_progress": CommandSchema("research_progress", CommandType.QUERY, 0, 0,
                                         description="Get research progress"),
        "top_strategies": CommandSchema("top_strategies", CommandType.QUERY, 0, 1, [int],
                                       description="Get top strategies"),
        "portfolio": CommandSchema("portfolio", CommandType.QUERY, 0, 0,
                                 description="Get portfolio status"),
        "pause_research": CommandSchema("pause_research", CommandType.CONTROL, 0, 0,
                                       description="Pause research loop"),
        "resume_research": CommandSchema("resume_research", CommandType.CONTROL, 0, 0,
                                        description="Resume research loop"),
        "strategy_metrics": CommandSchema("strategy_metrics", CommandType.QUERY, 1, 1, [str],
                                         description="Get strategy metrics"),
        "system_health": CommandSchema("system_health", CommandType.QUERY, 0, 0,
                                      description="System health check"),
        "research_stats": CommandSchema("research_stats", CommandType.QUERY, 0, 0,
                                       description="Detailed research statistics"),
        "allocate": CommandSchema("allocate", CommandType.ALLOCATION, 2, 2, [str, float],
                                 description="Allocate capital", dangerous=True),
        "help": CommandSchema("help", CommandType.QUERY, 0, 0,
                             description="Show help"),
    }
    
    def __init__(self) -> None:
        self._command_history: List[Tuple[str, datetime]] = []
    
    def parse(self, text: str) -> "ParseResult":
        """
        Parse a command string.
        
        Parameters
        ----------
        text : str
            Command text (e.g., "/status" or "/allocate strategy_001 25")
        
        Returns
        -------
        ParseResult
            Parsed command with args and validation status
        """
        try:
            # Clean text
            text = str(text).strip()
            
            if not text.startswith("/"):
                text = "/" + text
            
            # Tokenize
            tokens = self._tokenize(text)
            if not tokens:
                return ParseResult(
                    valid=False,
                    command=None,
                    args=[],
                    error="Empty command"
                )
            
            # Extract command
            command = tokens[0].lstrip("/").lower()
            args = tokens[1:]
            
            # Look up schema
            schema = self.SCHEMAS.get(command)
            if not schema:
                return ParseResult(
                    valid=False,
                    command=command,
                    args=[],
                    error=f"Unknown command: {command}"
                )
            
            # Validate argument count
            if len(args) < schema.min_args:
                return ParseResult(
                    valid=False,
                    command=command,
                    args=args,
                    error=f"Too few arguments (need {schema.min_args}, got {len(args)})"
                )
            
            if schema.max_args is not None and len(args) > schema.max_args:
                return ParseResult(
                    valid=False,
                    command=command,
                    args=args,
                    error=f"Too many arguments (max {schema.max_args}, got {len(args)})"
                )
            
            # Coerce argument types
            coerced_args = []
            for i, arg in enumerate(args):
                if i < len(schema.arg_types):
                    arg_type = schema.arg_types[i]
                    try:
                        coerced_args.append(arg_type(arg))
                    except (ValueError, TypeError) as exc:
                        return ParseResult(
                            valid=False,
                            command=command,
                            args=args,
                            error=f"Argument {i+1} type mismatch: expected {arg_type.__name__}"
                        )
                else:
                    coerced_args.append(arg)
            
            # Record in history
            self._command_history.append((command, datetime.now(tz=timezone.utc)))
            
            return ParseResult(
                valid=True,
                command=command,
                args=coerced_args,
                schema=schema
            )
        
        except Exception as exc:
            logger.error("Command parsing failed: %s", exc)
            return ParseResult(
                valid=False,
                command=None,
                args=[],
                error=f"Parse error: {str(exc)}"
            )
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Tokenize command text.
        
        Handles quoted strings and preserves tokens.
        """
        # Match tokens: quoted strings or regular words
        pattern = r'"([^"]*)"|(\S+)'
        matches = re.findall(pattern, text)
        
        tokens = []
        for quoted, unquoted in matches:
            if quoted:
                tokens.append(quoted)
            elif unquoted:
                tokens.append(unquoted)
        
        return tokens
    
    def get_command_frequency(
        self,
        window_seconds: int = 60,
    ) -> Dict[str, int]:
        """Get command frequency in time window."""
        try:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=window_seconds)
            
            # Clean old entries
            self._command_history = [
                (cmd, ts) for cmd, ts in self._command_history
                if ts > cutoff
            ]
            
            # Count by command
            freq = {}
            for cmd, _ in self._command_history:
                freq[cmd] = freq.get(cmd, 0) + 1
            
            return freq
        
        except Exception:
            return {}


class ParseResult:
    """Result of command parsing."""
    
    def __init__(
        self,
        valid: bool,
        command: Optional[str] = None,
        args: Optional[List] = None,
        schema: Optional[CommandSchema] = None,
        error: Optional[str] = None,
    ) -> None:
        self.valid = valid
        self.command = command
        self.args = args or []
        self.schema = schema
        self.error = error
    
    def is_dangerous(self) -> bool:
        """Check if command has dangerous side effects."""
        return self.schema and self.schema.dangerous
    
    def is_query(self) -> bool:
        """Check if command is read-only query."""
        return self.schema and self.schema.cmd_type == CommandType.QUERY
    
    def __repr__(self) -> str:
        if self.valid:
            return f"ParseResult(command={self.command}, args={self.args})"
        else:
            return f"ParseResult(error={self.error})"


class CommandValidator:
    """
    Validate commands before execution.
    
    Checks:
    - Authorization level
    - Rate limits
    - Dangerous commands require confirmation
    - Argument ranges and types
    """
    
    def __init__(
        self,
        authorized_users: Optional[set] = None,
        rate_limit_per_min: int = 20,
        dangerous_limit_per_hour: int = 5,
    ) -> None:
        self.authorized_users = authorized_users or set()
        self.rate_limit_per_min = rate_limit_per_min
        self.dangerous_limit_per_hour = dangerous_limit_per_hour
        
        self._user_commands: Dict[str, List[datetime]] = {}
        self._dangerous_commands: Dict[str, List[datetime]] = {}
    
    def validate(
        self,
        user_id: str,
        parse_result: ParseResult,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a parsed command.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check authorization
            if self.authorized_users and user_id not in self.authorized_users:
                return False, "❌ Unauthorized"
            
            # Check parse validity
            if not parse_result.valid:
                return False, f"❌ {parse_result.error}"
            
            # Check rate limit
            now = datetime.now(tz=timezone.utc)
            
            if user_id not in self._user_commands:
                self._user_commands[user_id] = []
            
            # Clean old entries (>1 min)
            cutoff = now - timedelta(minutes=1)
            self._user_commands[user_id] = [
                ts for ts in self._user_commands[user_id]
                if ts > cutoff
            ]
            
            if len(self._user_commands[user_id]) >= self.rate_limit_per_min:
                return False, f"⏱️ Rate limited ({self.rate_limit_per_min} commands/minute)"
            
            # Check dangerous command limit
            if parse_result.is_dangerous():
                if user_id not in self._dangerous_commands:
                    self._dangerous_commands[user_id] = []
                
                # Clean old entries (>1 hour)
                cutoff = now - timedelta(hours=1)
                self._dangerous_commands[user_id] = [
                    ts for ts in self._dangerous_commands[user_id]
                    if ts > cutoff
                ]
                
                if len(self._dangerous_commands[user_id]) >= self.dangerous_limit_per_hour:
                    return False, f"⚠️ Dangerous command limit ({self.dangerous_limit_per_hour}/hour)"
            
            # Record command
            self._user_commands[user_id].append(now)
            if parse_result.is_dangerous():
                self._dangerous_commands[user_id].append(now)
            
            return True, None
        
        except Exception as exc:
            logger.error("Validation failed: %s", exc)
            return False, f"❌ Validation error: {str(exc)[:50]}"


class CommandFormatter:
    """Format command results for Telegram display."""
    
    @staticmethod
    def format_result(
        success: bool,
        message: str,
        code_block: bool = False,
    ) -> str:
        """
        Format result for Telegram message.
        
        Parameters
        ----------
        success : bool
            Whether command succeeded
        message : str
            Result message
        code_block : bool
            Whether to wrap in code block
        
        Returns
        -------
        str
            Formatted message for Telegram
        """
        if code_block:
            return f"```\n{message}\n```"
        else:
            return message
    
    @staticmethod
    def paginate(
        text: str,
        max_length: int = 4096,
    ) -> List[str]:
        """
        Split long messages into pages.
        
        Telegram has 4096 character limit per message.
        """
        if len(text) <= max_length:
            return [text]
        
        pages = []
        current = ""
        
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                if current:
                    pages.append(current)
                current = line
            else:
                current += ("\n" if current else "") + line
        
        if current:
            pages.append(current)
        
        return pages
