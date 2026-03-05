class BaseATSAdapter:
    provider = None
    active = True

    def fetch(self, company):
        raise NotImplementedError

    def normalize(self, raw_job):
        raise NotImplementedError
