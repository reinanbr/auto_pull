#!/usr/bin/env python3
"""autopull/logger.py - Structured logging configuration for AutoPull."""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

DEFAULT_LOG_DIR = "/var/log/autopull"
DEFAULT_LOG_FILE = "autopull.log"


class ProjectFormatter(logging.Formatter):
    """Formatter that includes project metadata in every line."""

    def format(self, record: logging.LogRecord) -> str:
        """Format records as: [ISO8601] [LEVEL] [project] message."""
        if not hasattr(record, "project"):
            record.project = "-"
        return super().format(record)


def _resolve_log_dir() -> str:
    """Resolve writable log dir with a safe local-development fallback."""
    configured = os.environ.get("AUTOPULL_LOG_DIR", DEFAULT_LOG_DIR)
    try:
        os.makedirs(configured, exist_ok=True)
        return configured
    except OSError:
        fallback = "/tmp/autopull"
        os.makedirs(fallback, exist_ok=True)
        return fallback


def get_logger(
    name: str = "autopull", level: int = logging.INFO
) -> logging.Logger:
    """Create or return a configured AutoPull logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    log_dir = _resolve_log_dir()
    log_path = os.path.join(log_dir, DEFAULT_LOG_FILE)

    formatter = ProjectFormatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(project)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


def project_logger_adapter(
    logger: logging.Logger, project: Optional[str]
) -> logging.LoggerAdapter:
    """Return a LoggerAdapter with a project field set."""
    return logging.LoggerAdapter(logger, {"project": project or "-"})
