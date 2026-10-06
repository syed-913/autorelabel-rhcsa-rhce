"""Logging: one rolling app log plus per-operation logs. Secrets are redacted."""

from __future__ import annotations

import logging
import logging.handlers
import re
import time
from pathlib import Path

from . import paths

_REDACT = re.compile(r"(?i)(password|passwd|token|activation[_-]?key|secret)(\s*[=:]\s*|\s+)(\S+)")


def redact(text: str) -> str:
    return _REDACT.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup(debug: bool = False) -> logging.Logger:
    paths.ensure_workspace()
    logger = logging.getLogger("autorelabel")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        paths.LOGS / "autorelabel.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(_RedactingFormatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(handler)
    return logger


def get(name: str = "") -> logging.Logger:
    return logging.getLogger(f"autorelabel.{name}" if name else "autorelabel")


def operation_log(kind: str) -> Path:
    """A fresh log file for a long operation (box build, lab up, grading...)."""
    paths.ensure_workspace()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return paths.LOGS / f"{stamp}-{kind}.log"
