import logging
import sys


class SafeExtraFormatter(logging.Formatter):
    """
    Formatter, which:
    - always writes level + logger name + message
    - if fields are with `extra`, add them clearly
    - not breaking, when extra is empty
    """

    def format(self, record: logging.LogRecord) -> str:
        base = f"{record.levelname} {record.name}: {record.getMessage()}"

        # standard fields LogRecord
        reserved = {
            "name", "msg", "args", "levelname", "levelno",
            "pathname", "filename", "module", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process",
        }

        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in reserved
        }

        if extras:
            extra_str = " ".join(f"{k}={v}" for k, v in extras.items())
            return f"{base} | {extra_str}"

        return base


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

    formatter = SafeExtraFormatter()
    handler.setFormatter(formatter)

    # removing everything, logged earlier
    root.handlers.clear()
    root.addHandler(handler)
