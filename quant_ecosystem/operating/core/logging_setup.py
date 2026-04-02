"""Production logging bootstrap for Quant Ecosystem."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _ContainsNameFilter(logging.Filter):
    def __init__(self, tokens):
        super().__init__()
        self._tokens = tuple(str(token).lower() for token in tokens)

    def filter(self, record: logging.LogRecord) -> bool:
        name = str(record.name).lower()
        return any(token in name for token in self._tokens)


def configure_logging(base_dir: str | Path | None = None, level: int = logging.INFO) -> Path:
    root = logging.getLogger()
    if getattr(root, "_quant_logging_ready", False):
        return Path(getattr(root, "_quant_log_dir"))

    log_dir = Path(base_dir or "storage/logs").resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    system_handler = RotatingFileHandler(log_dir / "system.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    system_handler.setLevel(level)
    system_handler.setFormatter(formatter)
    root.addHandler(system_handler)

    execution_handler = RotatingFileHandler(log_dir / "execution.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    execution_handler.setLevel(level)
    execution_handler.setFormatter(formatter)
    execution_handler.addFilter(_ContainsNameFilter(["execution", "broker", "portfolio", "risk"]))
    root.addHandler(execution_handler)

    errors_handler = RotatingFileHandler(log_dir / "errors.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    errors_handler.setLevel(logging.ERROR)
    errors_handler.setFormatter(formatter)
    root.addHandler(errors_handler)

    root._quant_logging_ready = True  # type: ignore[attr-defined]
    root._quant_log_dir = str(log_dir)  # type: ignore[attr-defined]
    logging.getLogger(__name__).info("Structured logging initialized at %s", log_dir)
    return log_dir
