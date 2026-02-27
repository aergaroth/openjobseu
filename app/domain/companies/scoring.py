from datetime import datetime
from uuid import UUID
from typing import Optional

from .models import Company
from .repository import CompanyRepository
from storage.db_engine import get_connection


EU_COUNTRIES = {
    "PL", "DE", "FR", "ES", "IT", "NL", "SE", "FI", "DK",
    "IE", "PT", "BE", "AT", "CZ", "SK", "HU", "RO", "BG",
    "HR", "SI", "LT", "LV", "EE", "LU", "MT", "CY", "GR",
}


class CompanyScoringService:

    def __init__(self, repository: CompanyRepository):
        self.repository = repository

    def recompute_score(self, company: Company) -> int:
        score = 0

        # 1. Remote posture
        if company.remote_posture == "REMOTE_ONLY":
            score += 40
        elif company.remote_posture == "REMOTE_FRIENDLY":
            score += 20
        # UNKNOWN -> +0

        # 2. EU entity
        if company.eu_entity_verified:
            score += 25

        # 3. HQ in EU
        if company.hq_country in EU_COUNTRIES:
            score += 20

        # 4. Historical approval ratio
        approval_ratio = self._get_approval_ratio(company.company_id)

        if approval_ratio is not None:
            if approval_ratio >= 0.8:
                score += 15
            elif approval_ratio >= 0.5:
                score += 8

        return score

    def recompute_and_persist(self, company: Company) -> int:
        new_score = self.recompute_score(company)
        now = datetime.utcnow()

        self.repository.update_signal_score(
            company.company_id,
            new_score,
            now,
        )

        return new_score

    def _get_approval_ratio(self, company_id: UUID) -> Optional[float]:
        query = """
            SELECT
                COUNT(*) FILTER (WHERE compliance_status = 'approved') AS approved,
                COUNT(*) AS total
            FROM jobs
            WHERE company_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (company_id,))
                row = cur.fetchone()

        approved, total = row

        if total == 0:
            return None

        return approved / total
