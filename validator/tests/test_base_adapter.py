import pytest
import requests
from unittest.mock import MagicMock
from app.adapters.ats.base import ATSAdapter


class DummyAdapter(ATSAdapter):
    source_name = "dummy"

    def fetch(self, company, updated_since=None):
        return []

    def normalize(self, raw_job):
        return None

    def probe_jobs(self, slug):
        return {}


def test_parse_json_handles_decode_error():
    adapter = DummyAdapter()
    resp = MagicMock()
    resp.json.side_effect = requests.exceptions.JSONDecodeError("msg", "doc", 0)
    resp.text = "<html>502 Bad Gateway</html>"
    resp.status_code = 502

    with pytest.raises(ValueError, match="Dummy API returned non-JSON response"):
        adapter._parse_json(resp, "test-slug", context="probe")


def test_extract_salary_edge_cases():
    adapter = DummyAdapter()

    # Test na wartości stringowe (ułamkowe), powszechne w mniejszych systemach
    res = adapter.extract_salary({"min": "100.5", "max": "200.5", "currency": "eur", "interval": "monthly"})
    assert res["salary_min"] == 100
    assert res["salary_max"] == 200
    assert res["salary_currency"] == "EUR"
    assert res["salary_period"] == "monthly"

    # Zepsute wartości w payloadzie (odporność na KeyError/ValueError)
    res2 = adapter.extract_salary({"min": "unspecified", "max": None})
    assert res2["salary_min"] is None
    assert res2["salary_max"] is None


def test_build_description_resolves_fallbacks():
    adapter = DummyAdapter()
    raw = {"desc_html": "<b>Hi</b>", "reqs": "Python"}
    mapping = [(["missing", "desc_html"], None), ("reqs", "Requirements")]
    desc = adapter.build_description(raw, mapping)

    assert "<b>Hi</b>" in desc
    assert "<h3>Requirements</h3>\nPython" in desc


def test_filter_incremental_jobs():
    adapter = DummyAdapter()
    jobs = [
        {"id": 1, "created": "2023-01-01T00:00:00Z"},
        {"id": 2, "created": "2023-01-03T00:00:00Z"},
        {"id": 3},  # Brak daty na stanowisku (powinno przejść)
        "not a dict",  # Błędny format też powinien zostać zwrócony by nie wysypać rzutowania w runtime
    ]

    assert len(adapter._filter_incremental_jobs(jobs, None, ["created"])) == 4
    assert len(adapter._filter_incremental_jobs(jobs, "invalid", ["created"])) == 4

    filtered = adapter._filter_incremental_jobs(jobs, "2023-01-02T00:00:00Z", ["created"])
    assert len(filtered) == 3
