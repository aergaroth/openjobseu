# Development helper script
# Not used in production or CI

from ingestion.adapters.example_source import ExampleSourceAdapter
from app.workers.normalization.example_source import normalize_example_source_job
import json

adapter = ExampleSourceAdapter()
raw_jobs = adapter.fetch()
jobs = [normalize_example_source_job(job) for job in raw_jobs]

print(json.dumps(jobs, indent=2))
