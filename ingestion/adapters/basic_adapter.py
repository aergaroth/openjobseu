class SourceAdapter:
    SOURCE_ID = "example_source"

    def fetch(self) -> list[dict]:
        """Fetch raw jobs from the source."""
        pass

    def normalize(self, raw_job: dict) -> dict:
        """Map source data to canonical job model."""
        pass

    def run(self) -> list[dict]:
        raw_jobs = self.fetch()
        return [self.normalize(job) for job in raw_jobs]
