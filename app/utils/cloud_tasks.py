from __future__ import annotations

import base64
import json
import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def is_tick_queue_configured() -> bool:
    return bool(
        os.getenv("TICK_TASK_QUEUE_PROJECT")
        and os.getenv("TICK_TASK_QUEUE_LOCATION")
        and os.getenv("TICK_TASK_QUEUE_NAME")
    )


def create_tick_task(
    *,
    task_id: str,
    handler_url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    project_id = os.environ["TICK_TASK_QUEUE_PROJECT"]
    location = os.environ["TICK_TASK_QUEUE_LOCATION"]
    queue_name = os.environ["TICK_TASK_QUEUE_NAME"]
    parent = f"projects/{project_id}/locations/{location}/queues/{queue_name}"
    task_name = f"{parent}/tasks/tick-{task_id}"

    credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    session = AuthorizedSession(credentials)

    response = session.post(
        f"https://cloudtasks.googleapis.com/v2/{parent}/tasks",
        json={
            "task": {
                "name": task_name,
                "dispatchDeadline": os.getenv("TICK_TASK_DISPATCH_DEADLINE", "1800s"),
                "httpRequest": {
                    "httpMethod": "POST",
                    "url": handler_url,
                    "headers": headers,
                    "body": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8"),
                },
            }
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
