class BaseATSAdapter:
    provider = None
    active = True

    def fetch(self, company, updated_since=None):
        raise NotImplementedError

    def normalize(self, raw_job):
        raise NotImplementedError
