from typing import Any, Dict

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register

from app.adapters.ats.utils import (
    normalize_source_datetime,
    sanitize_location,
    sanitize_url,
    to_utc_datetime,
)
from app.utils.cleaning import clean_description

class LeverAdapter(ATSAdapter):
    source_name = "lever"
    active = False

    def fetch(self, company: Dict, updated_since: Any = None):
        raise NotImplementedError("Lever adapter is not implemented yet")

    def normalize(self, raw_job: Dict) -> Dict | None:
        raise NotImplementedError("Lever adapter is not implemented yet")

register(LeverAdapter.source_name, LeverAdapter)