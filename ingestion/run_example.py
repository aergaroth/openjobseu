from ingestion.adapters.example_source import ExampleSourceAdapter
import json

adapter = ExampleSourceAdapter()
jobs = adapter.run()

print(json.dumps(jobs, indent=2))
