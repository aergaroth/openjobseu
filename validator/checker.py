from datetime import datetime, timezone
import requests

from validator.rules import get_ttl_for_source


class AvailabilityChecker:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def check(self, job: dict) -> dict:
        now = datetime.now(timezone.utc)

        # Ensure counter exists
        job.setdefault("verification_failures", 0)

        ttl = get_ttl_for_source(job["source"])
        last_verified = job.get("last_verified_at")

        # TTL check first – stale jobs are not re-verified
        if last_verified:
            last_verified_dt = datetime.fromisoformat(last_verified)
            if now - last_verified_dt > ttl:
                job["status"] = "stale"
                return job

        try:
            response = requests.head(
                job["source_url"],
                timeout=self.timeout,
                allow_redirects=True,
            )

            if response.status_code in (404, 410):
                job["status"] = "expired"
            elif response.status_code < 400:
                job["status"] = "active"
                job["last_verified_at"] = now
                job["verification_failures"] = 0
            else:
                job["status"] = "unreachable"
                job["verification_failures"] += 1

        except Exception:
            job["status"] = "unreachable"
            job["verification_failures"] += 1

        return job
