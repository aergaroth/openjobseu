from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class Company:
    company_id: UUID
    legal_name: str
    brand_name: Optional[str]
    hq_country: str
    hq_city: Optional[str]
    eu_entity_verified: bool
    remote_posture: str
    ats_provider: Optional[str]
    ats_slug: Optional[str]
    ats_api_url: Optional[str]
    careers_url: Optional[str]
    signal_score: int
    signal_last_computed_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    bootstrap: bool
    approved_jobs_count: int
    last_approved_job_at: Optional[datetime]
