# Adapter responsibility:
# - fetch raw job data
# - MUST NOT normalize, set job lifecycle status, or perform availability checks


import json
from pathlib import Path


class ExampleSourceAdapter:
    SOURCE_ID = "example_source"

    def __init__(self):
        self.source_file = Path("ingestion/sources/example_jobs.json")

    def fetch(self) -> list[dict]:
        with self.source_file.open() as f:
            payload = json.load(f)
        return payload.get("jobs", [])
