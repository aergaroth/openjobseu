from sqlalchemy import text
from uuid import uuid4
from datetime import datetime


class CompanyResolverService:

    def __init__(self, repository):
        self.repository = repository

    def resolve_or_create(self, conn, company_name: str | None) -> str | None:
        if not company_name:
            return None

        normalized = self._normalize(company_name)

        existing = self.repository.get_by_legal_name(conn, normalized)
        if existing:
            return str(existing.company_id)

        return self._create_bootstrap(conn, normalized)

    def _create_bootstrap(self, conn, legal_name: str) -> str:
        company_id = uuid4()
        now = datetime.utcnow()

        insert_query = text("""
            INSERT INTO companies (
                company_id,
                legal_name,
                hq_country,
                eu_entity_verified,
                remote_posture,
                is_active,
                bootstrap,
                created_at,
                updated_at
            )
            VALUES (
                :company_id,
                :legal_name,
                'ZZ',
                false,
                'UNKNOWN',
                false,
                true,
                :now,
                :now
            )
            ON CONFLICT DO NOTHING
            RETURNING company_id
        """)

        result = conn.execute(insert_query, {
            "company_id": company_id,
            "legal_name": legal_name,
            "now": now
        })

        row = result.first()
        if row:
            return str(row[0])

        # conflict — somone could insert something in the same transaction
        existing = self.repository.get_by_legal_name(conn, legal_name)
        return str(existing.company_id)

    @staticmethod
    def _normalize(name: str) -> str:
        return " ".join(name.strip().split())
