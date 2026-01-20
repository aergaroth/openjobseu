from ingestion.adapters.example_source import ExampleSourceAdapter


REQUIRED_FIELDS = [
    "job_id",
    "source",
    "source_job_id",
    "source_url",
    "title",
    "company_name",
    "remote",
    "status",
    "created_at",
]


def test_adapter_produces_canonical_jobs():
    adapter = ExampleSourceAdapter()
    jobs = adapter.run()

    assert isinstance(jobs, list)
    assert len(jobs) > 0

    for job in jobs:
        for field in REQUIRED_FIELDS:
            assert field in job

def get_jobs():
    return ExampleSourceAdapter().run()

