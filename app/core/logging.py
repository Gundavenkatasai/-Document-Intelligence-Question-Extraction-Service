import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production log parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include standard context fields if passed in `extra`
        for key in ("document_id", "job_id", "page", "stage", "duration_ms", "failure_reason"):
            val = getattr(record, key, None)
            if val is not None:
                log_obj[key] = str(val)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(json_logs: bool = False, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("document_intelligence")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s (stage=%(stage)s doc=%(document_id)s): %(message)s"
        # Provide defaults for format keys
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                if not hasattr(record, "stage"):
                    record.stage = "-"
                if not hasattr(record, "document_id"):
                    record.document_id = "-"
                return super().format(record)

        handler.setFormatter(CustomFormatter(fmt))

    logger.addHandler(handler)
    return logger


logger = setup_logging()
