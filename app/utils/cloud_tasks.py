from __future__ import annotations

import base64
import json
import os
import logging
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession
import requests

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
logger = logging.getLogger(__name__)


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

    # Filtrujemy puste nagłówki (API Google zwraca 400, jeśli np. X-Scheduler-Job-Name to "")
    clean_headers = {k: v for k, v in headers.items() if v}

    # Usunięcie nagłówka Authorization, jeżeli chcemy przypiąć OIDC (API Cloud Tasks zgłosi konflikt i 400 Bad Request)
    if "Authorization" in clean_headers:
        del clean_headers["Authorization"]
    if "authorization" in clean_headers:
        del clean_headers["authorization"]

    task_payload = {
        "name": task_name,
        "dispatchDeadline": os.getenv("TICK_TASK_DISPATCH_DEADLINE", "1800s"),
        "httpRequest": {
            "httpMethod": "POST",
            "url": handler_url,
            "headers": clean_headers,
            "body": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8"),
        },
    }

    service_account_email = os.getenv("SCHEDULER_SA_EMAIL")
    audience = os.getenv("BASE_URL")

    if service_account_email and audience:
        task_payload["httpRequest"]["oidcToken"] = {
            "serviceAccountEmail": service_account_email,
            "audience": audience,
        }

    try:
        response = session.post(
            f"https://cloudtasks.googleapis.com/v2/{parent}/tasks",
            json={"task": task_payload},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_msg = e.response.text if e.response else str(e)
        logger.error(f"Cloud Tasks API Error: {error_msg}", extra={"payload": task_payload})
        raise
