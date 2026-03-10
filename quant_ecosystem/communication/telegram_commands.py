from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CommandType(Enum):
    QUERY = "query"
    CONTROL = "control"
    ADMIN = "admin"


@dataclass(frozen=True)
class CommandSchema:
    name: str
    cmd_type: CommandType
    min_args: int = 0
    max_args: Optional[int] = None
    description: str = ""
    dangerous: bool = False


@dataclass
class ParseResult:
    valid: bool
    command: Optional[str] = None
    args: Optional[List[str]] = None
    schema: Optional[CommandSchema] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.args is None:
            self.args = []

    def is_dangerous(self) -> bool:
        return bool(self.schema and self.schema.dangerous)

    def is_query(self) -> bool:
        return bool(self.schema and self.schema.cmd_type == CommandType.QUERY)


class CommandParser:
    SCHEMAS: Dict[str, CommandSchema] = {
        "status": CommandSchema("status", CommandType.QUERY, description="System status"),
        "start": CommandSchema("start", CommandType.CONTROL, description="Start trading"),
        "stop": CommandSchema("stop", CommandType.CONTROL, description="Stop trading"),
        "pause": CommandSchema("pause", CommandType.CONTROL, description="Pause research loop"),
        "resume": CommandSchema("resume", CommandType.CONTROL, description="Resume research loop"),
        "positions": CommandSchema("positions", CommandType.QUERY, description="Open positions"),
        "pnl": CommandSchema("pnl", CommandType.QUERY, description="P&L status"),
        "strategies": CommandSchema("strategies", CommandType.QUERY, description="Running strategies"),
        "research": CommandSchema("research", CommandType.QUERY, description="Research runtime status"),
        "shutdown": CommandSchema("shutdown", CommandType.ADMIN, description="Emergency shutdown", dangerous=True),
        "help": CommandSchema("help", CommandType.QUERY, description="Show help"),
    }

    def __init__(self) -> None:
        self._command_history: List[Tuple[str, datetime]] = []

    def parse(self, text: str) -> ParseResult:
        text = str(text or "").strip()
        if not text:
            return ParseResult(valid=False, error="Empty command")

        if not text.startswith("/"):
            text = f"/{text}"

        tokens = self._tokenize(text)
        if not tokens:
            return ParseResult(valid=False, error="Empty command")

        command = tokens[0].lstrip("/").lower()
        args = tokens[1:]
        schema = self.SCHEMAS.get(command)
        if schema is None:
            return ParseResult(valid=False, command=command, args=args, error=f"Unknown command: {command}")

        if len(args) < schema.min_args:
            return ParseResult(valid=False, command=command, args=args, error="Too few arguments")

        if schema.max_args is not None and len(args) > schema.max_args:
            return ParseResult(valid=False, command=command, args=args, error="Too many arguments")

        self._command_history.append((command, datetime.now(tz=timezone.utc)))
        return ParseResult(valid=True, command=command, args=args, schema=schema)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        pattern = r'"([^"]*)"|(\S+)'
        tokens: List[str] = []
        for quoted, plain in re.findall(pattern, text):
            if quoted:
                tokens.append(quoted)
            elif plain:
                tokens.append(plain)
        return tokens

    def get_command_frequency(self, window_seconds: int = 60) -> Dict[str, int]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=window_seconds)
        self._command_history = [
            (cmd, ts) for cmd, ts in self._command_history if ts >= cutoff
        ]
        counts: Dict[str, int] = {}
        for command, _ in self._command_history:
            counts[command] = counts.get(command, 0) + 1
        return counts


class CommandValidator:
    def __init__(
        self,
        authorized_users: Optional[set] = None,
        rate_limit_per_min: int = 20,
        dangerous_limit_per_hour: int = 5,
    ) -> None:
        self.authorized_users = authorized_users or set()
        self.rate_limit_per_min = int(rate_limit_per_min)
        self.dangerous_limit_per_hour = int(dangerous_limit_per_hour)
        self._user_commands: Dict[str, List[datetime]] = {}
        self._dangerous_commands: Dict[str, List[datetime]] = {}

    def validate(self, user_id: str, parse_result: ParseResult) -> Tuple[bool, Optional[str]]:
        try:
            if self.authorized_users and user_id not in self.authorized_users:
                return False, "Unauthorized"

            if not parse_result.valid:
                return False, parse_result.error

            now = datetime.now(tz=timezone.utc)
            user_entries = self._user_commands.setdefault(user_id, [])
            user_cutoff = now - timedelta(minutes=1)
            self._user_commands[user_id] = [ts for ts in user_entries if ts >= user_cutoff]
            if len(self._user_commands[user_id]) >= self.rate_limit_per_min:
                return False, "Rate limited"

            if parse_result.is_dangerous():
                danger_entries = self._dangerous_commands.setdefault(user_id, [])
                danger_cutoff = now - timedelta(hours=1)
                self._dangerous_commands[user_id] = [ts for ts in danger_entries if ts >= danger_cutoff]
                if len(self._dangerous_commands[user_id]) >= self.dangerous_limit_per_hour:
                    return False, "Dangerous command rate limited"
                self._dangerous_commands[user_id].append(now)

            self._user_commands[user_id].append(now)
            return True, None
        except Exception as exc:
            logger.warning("[telegram] command validation failed: %s", exc)
            return False, "Validation failed"


class CommandFormatter:
    @staticmethod
    def format_result(success: bool, message: str, code_block: bool = False) -> str:
        if code_block:
            return f"```\n{message}\n```"
        return message

    @staticmethod
    def paginate(text: str, max_length: int = 4096) -> List[str]:
        if len(text) <= max_length:
            return [text]

        pages: List[str] = []
        current = ""
        for line in text.splitlines():
            next_value = f"{current}\n{line}" if current else line
            if len(next_value) > max_length and current:
                pages.append(current)
                current = line
            else:
                current = next_value

        if current:
            pages.append(current)

        return pages
