from ingestion.adapters.example_source import ExampleSourceAdapter
from app.workers.normalization.example_source import normalize_example_source_job


REQUIRED_FIELDS = [
    "job_id",
    "source",
    "source_job_id",
    "source_url",
    "title",
    "company_name",
    "remote_source_flag",
    "status",
    "created_at",
]


def test_example_source_produces_canonical_jobs():
    adapter = ExampleSourceAdapter()
    raw_jobs = adapter.fetch()
    jobs = [normalize_example_source_job(job) for job in raw_jobs]

    assert isinstance(jobs, list)
    assert len(jobs) > 0

    for job in jobs:
        for field in REQUIRED_FIELDS:
            assert field in job

def get_jobs():
    adapter = ExampleSourceAdapter()
    return [normalize_example_source_job(job) for job in adapter.fetch()]
