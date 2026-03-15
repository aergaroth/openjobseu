from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domain.companies.scoring import CompanyScoringRules, EU_COUNTRIES


def update_company_job_stats_bulk(conn: Connection) -> int:
    result = conn.execute(text("""
        UPDATE companies c
        SET approved_jobs_count = COALESCE(ac.approved_cnt, 0),
            rejected_jobs_count = COALESCE(ac.rejected_cnt, 0),
            total_jobs_count = COALESCE(ac.total_cnt, 0),
            last_active_job_at = ac.last_active,
            updated_at = NOW()
        FROM (
            SELECT
                c2.company_id,
                COUNT(j.job_id) AS total_cnt,
                COUNT(j.job_id) FILTER (WHERE j.compliance_status = 'approved') AS approved_cnt,
                COUNT(j.job_id) FILTER (WHERE j.compliance_status = 'rejected') AS rejected_cnt,
                MAX(j.first_seen_at) FILTER (WHERE j.status = 'active') AS last_active
            FROM companies c2
            LEFT JOIN jobs j ON c2.company_id = j.company_id
            GROUP BY c2.company_id
        ) ac
        WHERE c.company_id = ac.company_id
          AND (
              COALESCE(c.approved_jobs_count, -1) != COALESCE(ac.approved_cnt, 0)
              OR COALESCE(c.rejected_jobs_count, -1) != COALESCE(ac.rejected_cnt, 0)
              OR COALESCE(c.total_jobs_count, -1) != COALESCE(ac.total_cnt, 0)
              OR c.last_active_job_at IS DISTINCT FROM ac.last_active
          );
    """))
    return result.rowcount


def update_company_signal_scores_bulk(conn: Connection) -> int:
    eu_countries_formatted = ", ".join(f"'{c}'" for c in EU_COUNTRIES)

    result = conn.execute(text(f"""
        UPDATE companies c
        SET signal_score = COALESCE(new_score.score, 0),
            signal_last_computed_at = NOW(),
            updated_at = NOW()
        FROM (
            SELECT
                c2.company_id,
                CAST(ROUND((
                    CASE WHEN c2.remote_posture = 'REMOTE_ONLY' THEN {CompanyScoringRules.REMOTE_ONLY_POINTS}
                         WHEN c2.remote_posture = 'REMOTE_FRIENDLY' THEN {CompanyScoringRules.REMOTE_FRIENDLY_POINTS}
                         ELSE 0 END
                    +
                    CASE WHEN c2.eu_entity_verified THEN {CompanyScoringRules.EU_ENTITY_POINTS} ELSE 0 END
                    +
                    CASE WHEN c2.hq_country IN ({eu_countries_formatted}) THEN {CompanyScoringRules.EU_HQ_POINTS} ELSE 0 END
                    +
                    CASE
                         WHEN stats.total > 0 AND (CAST(stats.approved AS NUMERIC) / NULLIF(stats.total, 0)) >= {CompanyScoringRules.APPROVAL_RATIO_HIGH_THRESHOLD} THEN {CompanyScoringRules.APPROVAL_RATIO_HIGH_POINTS}
                         WHEN stats.total > 0 AND (CAST(stats.approved AS NUMERIC) / NULLIF(stats.total, 0)) >= {CompanyScoringRules.APPROVAL_RATIO_MID_THRESHOLD} THEN {CompanyScoringRules.APPROVAL_RATIO_MID_POINTS}
                         ELSE 0 END
                ) * (
                    CASE
                         WHEN stats.total > 0 AND (CAST(stats.transparent AS NUMERIC) / NULLIF(stats.total, 0)) >= {CompanyScoringRules.TRANSPARENCY_RATIO_THRESHOLD} THEN {CompanyScoringRules.TRANSPARENCY_MULTIPLIER}
                         ELSE 1.0 END
                )) AS INTEGER) AS score
            FROM companies c2
            LEFT JOIN (
                SELECT
                    company_id,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE compliance_status = 'approved') AS approved,
                    COUNT(*) FILTER (WHERE salary_transparency_status = 'disclosed') AS transparent
                FROM jobs
                GROUP BY company_id
            ) stats ON c2.company_id = stats.company_id
        ) new_score
        WHERE c.company_id = new_score.company_id
          AND COALESCE(c.signal_score, -1) != COALESCE(new_score.score, 0);
    """))
    return result.rowcount