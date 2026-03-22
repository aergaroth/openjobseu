from app.adapters.ats.greenhouse import GreenhouseAdapter


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def test_remote_keyword_detection():
    adapter = GreenhouseAdapter()
    adapter.session.get = lambda url, timeout: DummyResponse(
        {
            "jobs": [
                {"title": "Remote Engineer", "location": "Anywhere"},
                {"title": "Office Analyst", "location": "Berlin"},
                {"title": "Distributed Systems", "location": "Remote"},
            ]
        }
    )

    result = adapter.probe_jobs("test-company")

    assert result["jobs_total"] == 3
    assert result["remote_hits"] == 2
    assert result["recent_job_at"] is None
