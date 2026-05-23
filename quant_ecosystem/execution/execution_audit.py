import json
from datetime import datetime
from pathlib import Path

AUDIT_LOG = Path("logs/execution_audit.jsonl")


def log_execution_event(payload: dict):
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

        enriched = {
            "timestamp": datetime.utcnow().isoformat(),
            **payload,
        }

        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(enriched) + "\n")

    except Exception:
        pass