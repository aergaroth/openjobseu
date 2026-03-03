from datetime import datetime
from uuid import uuid4
from typing import Iterable

from sqlalchemy import text, bindparam

from storage.db_engine import get_engine
from .models import Company


class CompanyRepository:

    # ----------------------------
    # READ
    # ----------------------------

    def get_many_by_legal_names(self, conn, names: set[str]) -> dict[str, Company]:
        """
        Zwraca mapę:
        lower(legal_name) -> Company
        """

        if not names:
            return {}

        lowered = [n.lower() for n in names]

        query = text("""
            SELECT *
            FROM companies
            WHERE LOWER(legal_name) IN :names
        """).bindparams(bindparam("names", expanding=True))

        rows = conn.execute(query, {"names": lowered}).mappings().all()

        return {
            row["legal_name"].lower(): Company(**row)
            for row in rows
        }

    # ----------------------------
    # WRITE - BOOTSTRAP
    # ----------------------------

    def bulk_create_bootstrap(self, conn, names: set[str]) -> None:
        """
        Tworzy bootstrap companies dla brakujących nazw.
        ON CONFLICT DO NOTHING zabezpiecza przed race condition.
        """

        if not names:
            return

        now = datetime.utcnow()

        rows = [{
            "company_id": uuid4(),
            "legal_name": name,
            "now": now
        } for name in names]

        query = text("""
            INSERT INTO companies (
                company_id,
                legal_name,
                hq_country,
                eu_entity_verified,
                remote_posture,
                is_active,
                bootstrap,
                signal_score,
                approved_jobs_count,
                created_at,
                updated_at
            )
            VALUES (
                :company_id,
                :legal_name,
                'ZZ',
                false,
                'UNKNOWN',
                true,
                true,
                0,
                0,
                :now,
                :now
            )
            ON CONFLICT DO NOTHING
        """)

        conn.execute(query, rows)

    # ----------------------------
    # WRITE - CURATED BATCH UPSERT
    # ----------------------------

    def batch_upsert_curated(self, conn, companies: list[dict]) -> None:
        """
        Upsert curated companies.
        Bootstrap -> curated upgrade.
        """

        if not companies:
            return

        now = datetime.utcnow()

        rows = [{
            "company_id": company.get("company_id", uuid4()),
            "legal_name": company["legal_name"],
            "hq_country": company["hq_country"],
            "eu_entity_verified": company.get("eu_entity_verified", False),
            "remote_posture": company["remote_posture"],
            "ats_provider": company.get("ats_provider"),
            "ats_slug": company.get("ats_slug"),
            "ats_api_url": company.get("ats_api_url"),
            "careers_url": company.get("careers_url"),
            "now": now
        } for company in companies]

        query = text("""
            INSERT INTO companies (
                company_id,
                legal_name,
                hq_country,
                eu_entity_verified,
                remote_posture,
                ats_provider,
                ats_slug,
                ats_api_url,
                careers_url,
                bootstrap,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :company_id,
                :legal_name,
                :hq_country,
                :eu_entity_verified,
                :remote_posture,
                :ats_provider,
                :ats_slug,
                :ats_api_url,
                :careers_url,
                false,
                true,
                :now,
                :now
            )
            ON CONFLICT DO UPDATE SET
                hq_country = EXCLUDED.hq_country,
                eu_entity_verified = EXCLUDED.eu_entity_verified,
                remote_posture = EXCLUDED.remote_posture,
                ats_provider = EXCLUDED.ats_provider,
                ats_slug = EXCLUDED.ats_slug,
                ats_api_url = EXCLUDED.ats_api_url,
                careers_url = EXCLUDED.careers_url,
                bootstrap = false,
                is_active = true,
                updated_at = EXCLUDED.updated_at
        """)

        conn.execute(query, rows)
