import json
import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    # Use DEBUG level for local development, INFO for others
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

    root_logger = logging.getLogger()

    # Clear existing handlers to prevent duplicate formatting issues
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if settings.ENVIRONMENT in ("production", "staging"):
        # Structured JSON formatter for log aggregation systems
        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_record = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "logger": record.name,
                    "module": record.module,
                    "func": record.funcName,
                    "lineno": record.lineno,
                }
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_record)

        formatter = JSONFormatter()
    else:
        # Clean developer-friendly CLI coloring/formatting
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


# Run setup on initialization
setup_logging()
logger = logging.getLogger("payment_service")
