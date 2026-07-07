# src/core/logging.py - NEW

import json
import logging
from datetime import datetime
from typing import Any, Dict


class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logs"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        # Add context if present
        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id
        if hasattr(record, "upload_id"):
            log_entry["upload_id"] = record.upload_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Add extra fields
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Get a structured logger"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
