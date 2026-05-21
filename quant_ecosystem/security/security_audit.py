import hashlib
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from quant_ecosystem.core.market_mode import MarketModeController


class SecurityAuditTrail:
    LOG_PATH = Path("logs/security_audit.jsonl")

    @classmethod
    def _git(cls, arg):
        try:
            return subprocess.check_output(
                ["git", arg],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except Exception:
            return "UNKNOWN"

    @classmethod
    def _hash_args(cls, args):
        try:
            raw = json.dumps(args, sort_keys=True, default=str)
            return hashlib.sha256(raw.encode()).hexdigest()
        except Exception:
            return "HASH_ERROR"

    @classmethod
    def log_event(
        cls,
        user_id,
        role,
        command,
        args,
        approval_used,
        result,
        break_glass=False
    ):
        try:
            cls.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

            payload = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "user_id": str(user_id),
                "role": str(role),
                "command": str(command),
                "args_hash": cls._hash_args(args),
                "approval_used": bool(approval_used),
                "result": str(result),
                "hostname": socket.gethostname(),
                "branch": cls._git("rev-parse --abbrev-ref HEAD"),
                "commit": cls._git("rev-parse --short HEAD"),
                "market_mode": str(MarketModeController.get_mode()),
                "break_glass": bool(break_glass),
            }

            with cls.LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")

        except Exception:
            pass