import hashlib
import hmac
import json
from datetime import datetime
from pathlib import Path


class TelegramAuditLogger:

    def __init__(self, secret, output_path="reporting/output/audit/telegram_actions.jsonl"):
        self.secret = (secret or "telegram-audit-default").encode("utf-8")
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_sig = ""

    def log(self, actor_id, role, action, result, page, chat_id):
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "actor_id": str(actor_id),
            "role": role,
            "action": str(action),
            "result": str(result),
            "page": str(page),
            "chat_id": str(chat_id),
            "prev_sig": self._last_sig,
        }
        canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = hmac.new(self.secret, canonical, hashlib.sha256).hexdigest()
        entry["sig"] = sig
        self._last_sig = sig

        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")
