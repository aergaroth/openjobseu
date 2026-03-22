from sqlalchemy import text
from storage.db_engine import get_engine

from app.domain.companies.scoring import CompanyScoringRules, EU_COUNTRIES


def update_company_job_stats_bulk() -> int:
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    last_id = "00000000-0000-0000-0000-000000000000"

    while True:
        with engine.begin() as conn:
            batch_rows = conn.execute(
                text("""
                SELECT company_id 
                FROM companies 
                WHERE company_id > :last_id 
                ORDER BY company_id 
                LIMIT :batch_size
            """),
                {"last_id": last_id, "batch_size": batch_size},
            ).fetchall()

            if not batch_rows:
                break

            company_ids = [str(r[0]) for r in batch_rows]
            company_ids_str = ", ".join(f"'{cid}'" for cid in company_ids)

            result = conn.execute(
                text(f"""
                WITH ac AS (
                    SELECT
                        c2.company_id,
                        COUNT(j.job_id) AS total_cnt,
                        COUNT(j.job_id) FILTER (WHERE j.compliance_status = 'approved') AS approved_cnt,
                        COUNT(j.job_id) FILTER (WHERE j.compliance_status = 'rejected') AS rejected_cnt,
                        MAX(j.first_seen_at) FILTER (WHERE j.status = 'active') AS last_active
                    FROM companies c2
                    LEFT JOIN jobs j ON c2.company_id = j.company_id
                    WHERE c2.company_id IN ({company_ids_str})
                    GROUP BY c2.company_id
                )
                UPDATE companies c
                SET approved_jobs_count = COALESCE(ac.approved_cnt, 0),
                    rejected_jobs_count = COALESCE(ac.rejected_cnt, 0),
                    total_jobs_count = COALESCE(ac.total_cnt, 0),
                    last_active_job_at = ac.last_active,
                    updated_at = NOW()
                FROM ac
                WHERE c.company_id = ac.company_id
                  AND (
                      COALESCE(c.approved_jobs_count, -1) != COALESCE(ac.approved_cnt, 0)
                      OR COALESCE(c.rejected_jobs_count, -1) != COALESCE(ac.rejected_cnt, 0)
                      OR COALESCE(c.total_jobs_count, -1) != COALESCE(ac.total_cnt, 0)
                      OR c.last_active_job_at IS DISTINCT FROM ac.last_active
                  );
            """)
            )

            total_updated += result.rowcount
            last_id = company_ids[-1]

    return total_updated


def update_company_remote_posture_bulk() -> int:
    engine = get_engine()
    batch_size = 1000
    total_updated = 0
    last_id = "00000000-0000-0000-0000-000000000000"

    while True:
        with engine.begin() as conn:
            batch_rows = conn.execute(
                text("""
                SELECT company_id 
                FROM companies 
                WHERE company_id > :last_id 
                ORDER BY company_id 
                LIMIT :batch_size
            """),
                {"last_id": last_id, "batch_size": batch_size},
            ).fetchall()

            if not batch_rows:
                break

            company_ids = [str(r[0]) for r in batch_rows]
            company_ids_str = ", ".join(f"'{cid}'" for cid in company_ids)

            result = conn.execute(
                text(f"""
                WITH remote_counts AS (
                    SELECT company_id, COUNT(job_id) as remote_jobs_count
                    FROM jobs
                    WHERE company_id IN ({company_ids_str})
                      AND remote_source_flag = TRUE
                    GROUP BY company_id
                    HAVING COUNT(job_id) >= 3
                )
                UPDATE companies c
                SET remote_posture = 'REMOTE_FRIENDLY',
                    updated_at = NOW()
                FROM remote_counts rc
                WHERE c.company_id = rc.company_id
                  AND c.remote_posture = 'UNKNOWN';
            """)
            )

            total_updated += result.rowcount
            last_id = company_ids[-1]

    return total_updated


def update_company_signal_scores_bulk() -> int:
    engine = get_engine()
    eu_countries_formatted = ", ".join(f"'{c}'" for c in EU_COUNTRIES)
    batch_size = 1000
    total_updated = 0
    last_id = "00000000-0000-0000-0000-000000000000"

    while True:
        with engine.begin() as conn:
            batch_rows = conn.execute(
                text("""
                SELECT company_id 
                FROM companies 
                WHERE company_id > :last_id 
                ORDER BY company_id 
                LIMIT :batch_size
            """),
                {"last_id": last_id, "batch_size": batch_size},
            ).fetchall()

            if not batch_rows:
                break

            company_ids = [str(r[0]) for r in batch_rows]
            company_ids_str = ", ".join(f"'{cid}'" for cid in company_ids)

            result = conn.execute(
                text(f"""
                WITH batch_companies AS (
                    SELECT c.*
                    FROM companies c
                    WHERE c.company_id IN ({company_ids_str})
                ),
                stats AS (
                    SELECT
                        bc.company_id,
                        COUNT(j.job_id) AS total,
                        COUNT(j.job_id) FILTER (WHERE j.compliance_status = 'approved') AS approved,
                        COUNT(j.job_id) FILTER (WHERE j.salary_transparency_status = 'disclosed') AS transparent
                    FROM batch_companies bc
                    LEFT JOIN jobs j ON bc.company_id = j.company_id
                    GROUP BY bc.company_id
                ),
                new_score AS (
                    SELECT
                        bc.company_id,
                        CAST(ROUND((
                            CASE WHEN bc.remote_posture = 'REMOTE_ONLY' THEN {CompanyScoringRules.REMOTE_ONLY_POINTS}
                                 WHEN bc.remote_posture = 'REMOTE_FRIENDLY' THEN {CompanyScoringRules.REMOTE_FRIENDLY_POINTS}
                                 ELSE 0 END
                            +
                            CASE WHEN bc.eu_entity_verified THEN {CompanyScoringRules.EU_ENTITY_POINTS} ELSE 0 END
                            +
                            CASE WHEN bc.hq_country IN ({eu_countries_formatted}) THEN {CompanyScoringRules.EU_HQ_POINTS} ELSE 0 END
                            +
                            CASE
                                 WHEN s.total > 0 AND (CAST(s.approved AS NUMERIC) / NULLIF(s.total, 0)) >= {CompanyScoringRules.APPROVAL_RATIO_HIGH_THRESHOLD} THEN {CompanyScoringRules.APPROVAL_RATIO_HIGH_POINTS}
                                 WHEN s.total > 0 AND (CAST(s.approved AS NUMERIC) / NULLIF(s.total, 0)) >= {CompanyScoringRules.APPROVAL_RATIO_MID_THRESHOLD} THEN {CompanyScoringRules.APPROVAL_RATIO_MID_POINTS}
                                 ELSE 0 END
                        ) * (
                            CASE
                                 WHEN s.total > 0 AND (CAST(s.transparent AS NUMERIC) / NULLIF(s.total, 0)) >= {CompanyScoringRules.TRANSPARENCY_RATIO_THRESHOLD} THEN {CompanyScoringRules.TRANSPARENCY_MULTIPLIER}
                                 ELSE 1.0 END
                        )) AS INTEGER) AS score
                    FROM batch_companies bc
                    JOIN stats s ON bc.company_id = s.company_id
                )
                UPDATE companies c
                SET signal_score = COALESCE(ns.score, 0),
                    signal_last_computed_at = NOW(),
                    updated_at = NOW()
                FROM new_score ns
                WHERE c.company_id = ns.company_id
                  AND COALESCE(c.signal_score, -1) != COALESCE(ns.score, 0);
            """)
            )

            total_updated += result.rowcount
            last_id = company_ids[-1]

    return total_updated
