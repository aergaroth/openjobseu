import logging
import json
import os
import sys
from datetime import datetime, timezone


RESERVED_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class SafeExtraFormatter(logging.Formatter):
    """
    Formatter, which:
    - always writes level + logger name + message
    - if fields are with `extra`, add them clearly
    - not breaking, when extra is empty
    """

    def format(self, record: logging.LogRecord) -> str:
        base = f"{record.levelname} {record.name}: {record.getMessage()}"
        extras = extract_record_extras(record)

        if extras:
            extra_str = " ".join(f"{k}={v}" for k, v in extras.items())
            return f"{base} | {extra_str}"

        return base


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        payload.update(extract_record_extras(record))

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(payload, ensure_ascii=False, default=str)


def extract_record_extras(record: logging.LogRecord) -> dict:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in RESERVED_LOG_RECORD_FIELDS and value is not None
    }


def is_container_runtime() -> bool:
    return bool(
        os.path.exists("/.dockerenv")
        or os.getenv("K_SERVICE")
        or os.getenv("ECS_CONTAINER_METADATA_URI")
        or os.getenv("KUBERNETES_SERVICE_HOST")
    )


def should_use_text_logs() -> bool:
    app_runtime = os.getenv("APP_RUNTIME")
    if app_runtime is not None:
        return app_runtime.strip().lower() == "local"

    return not is_container_runtime()


def configure_logging() -> None:
    """
    Global logging configuration for OpenJobsEU.

    Rules:
    - single StreamHandler (stdout)
    - INFO level by default
    - structured extras supported
    """

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    if should_use_text_logs():
        formatter = SafeExtraFormatter()
    else:
        formatter = JsonLogFormatter()

    handler.setFormatter(formatter)

    # removing everything, logged earlier
    root.handlers.clear()
    root.addHandler(handler)
