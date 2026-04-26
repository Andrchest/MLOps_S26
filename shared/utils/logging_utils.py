import logging
import json
import os
from asgi_correlation_id import CorrelationIdFilter


class JSONFormatter(logging.Formatter):
    def __init__(self, service_name):
        super(JSONFormatter, self).__init__()
        self.service_name: str = service_name

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "logger": record.name,
            "filename": record.filename,
            "lineno": record.lineno,
            "pathname": record.pathname,
            "process": record.process,
            "thread": record.thread,
            "correlation_id": getattr(record, "correlation_id", None),
        }

        standard_attrs = vars(logging.LogRecord("", 0, "", 0, "", (), None))
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_record[key] = value

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging(service_name: str):
    logger = logging.getLogger()
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter(service_name))
    handler.addFilter(CorrelationIdFilter())
    logger.addHandler(handler)
    return logger
