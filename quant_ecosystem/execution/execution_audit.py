import json
from datetime import datetime
from pathlib import Path


AUDIT_LOG = Path("logs/execution_audit.jsonl")


def log_execution_event(payload: dict):
    try:
        AUDIT_LOG.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        enriched = {
            "timestamp": datetime.utcnow().isoformat(),
            **payload,
        }

        with AUDIT_LOG.open(
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                json.dumps(enriched) + "\n"
            )

    except Exception:
        pass


def load_execution_events():
    if not AUDIT_LOG.exists():
        return []

    rows = []

    try:
        with AUDIT_LOG.open(
            "r",
            encoding="utf-8",
        ) as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    rows.append(
                        json.loads(line)
                    )
                except Exception:
                    continue

    except Exception:
        return []

    return rows