import logging
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Dict


def get_service_name() -> str:
    return os.getenv("SERVICE_NAME", "unknown")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": get_service_name(),
            "event": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(record.extra_fields)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


class StructuredLogger:
    def __init__(self, name: str, service_name: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.service_name = service_name or get_service_name()
        if not self.logger.handlers:
            self._setup_handler()

    def _setup_handler(self):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _log(self, level: int, event: str, **kwargs: Any):
        extra = {"extra_fields": kwargs} if kwargs else {}
        self.logger.log(level, event, extra=extra)

    def debug(self, event: str, **kwargs: Any):
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any):
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any):
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any):
        self._log(logging.ERROR, event, **kwargs)

    def critical(self, event: str, **kwargs: Any):
        self._log(logging.CRITICAL, event, **kwargs)


def setup_logger(name: str, service_name: Optional[str] = None) -> StructuredLogger:
    return StructuredLogger(name, service_name)


def get_correlation_id() -> str:
    return str(uuid.uuid4())


class CorrelationLogger(StructuredLogger):
    def __init__(self, name: str, service_name: Optional[str] = None, correlation_id: Optional[str] = None):
        super().__init__(name, service_name)
        self.correlation_id = correlation_id or get_correlation_id()

    def _log(self, level: int, event: str, **kwargs: Any):
        kwargs["correlation_id"] = self.correlation_id
        super()._log(level, event, **kwargs)
