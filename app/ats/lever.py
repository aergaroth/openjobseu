from app.ats.base import BaseATSAdapter
from app.ats.registry import register


class LeverAdapter(BaseATSAdapter):
    provider = "lever"
    active = False

    def fetch(self, company, updated_since=None):
        raise NotImplementedError("Lever adapter is not implemented yet")

    def normalize(self, raw_job):
        raise NotImplementedError("Lever adapter is not implemented yet")


register(LeverAdapter.provider, LeverAdapter)
