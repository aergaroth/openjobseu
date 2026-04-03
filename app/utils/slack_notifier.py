"""
Slack incoming webhook notifier — fire-and-forget alerts for pipeline failures.

Never raises exceptions. If the webhook call fails, the error is logged
and execution continues normally.

Usage:
    from app.utils.slack_notifier import notify_tick_failure

    notify_tick_failure(tick_id="abc", failed_steps=["ingestion"], duration_ms=3200)
"""

import json
import logging
import os
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("openjobseu.runtime")

_COLOUR_ERROR = "#ED4245"
_COLOUR_WARN = "#FEE75C"


def _env_label() -> str:
    mode = os.getenv("INGESTION_MODE", "local").upper()
    return f"[{mode}]"


def _send(payload: dict) -> None:
    """POST JSON payload to SLACK_WEBHOOK_URL. Silently swallows all errors."""
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return
    try:
        data = json.dumps(payload, ensure_ascii=False).encode()
        req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=5) as resp:
            if resp.status not in (200, 204):
                logger.warning("slack_webhook_unexpected_status", extra={"status": resp.status})
    except URLError as exc:
        logger.warning("slack_webhook_failed", extra={"error": str(exc)})
    except Exception as exc:
        logger.warning("slack_webhook_failed", extra={"error": str(exc)})


def notify_tick_failure(
    *,
    tick_id: str | None,
    failed_steps: list[str],
    sources_failed: int = 0,
    duration_ms: int = 0,
) -> None:
    """Send a Slack alert when a pipeline tick has failed steps."""
    env = _env_label()
    steps_fmt = ", ".join(f"`{s}`" for s in failed_steps) if failed_steps else "unknown"

    fields = [
        {"title": "Failed steps", "value": steps_fmt, "short": False},
        {"title": "Sources failed", "value": str(sources_failed), "short": True},
        {"title": "Duration", "value": f"{duration_ms / 1000:.1f}s", "short": True},
    ]
    if tick_id:
        fields.append({"title": "Tick ID", "value": f"`{tick_id}`", "short": False})

    _send(
        {
            "attachments": [
                {
                    "color": _COLOUR_ERROR,
                    "title": f"{env} ⚠️ Pipeline tick failed",
                    "fields": fields,
                    "fallback": f"{env} Pipeline tick failed — steps: {steps_fmt}",
                }
            ]
        }
    )
