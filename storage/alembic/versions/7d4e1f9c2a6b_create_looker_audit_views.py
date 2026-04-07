"""create looker audit views

Revision ID: 7d4e1f9c2a6b
Revises: 5c1b4a3e2f0d
Create Date: 2026-04-06 11:30:00.000000+00:00

Creates dedicated reporting views for the private Looker Studio audit dashboard.
The drill-down views are intentionally capped to avoid Looker Studio's silent
row truncation behavior on larger result sets.
"""

from alembic import op
import sqlalchemy as sa


revision = "7d4e1f9c2a6b"
down_revision = "5c1b4a3e2f0d"
branch_labels = None
depends_on = None


VIEW_NAMES = [
    "vw_looker_audit_overview",
    "vw_looker_audit_company_stats",
    "vw_looker_audit_source_7d",
    "vw_looker_audit_source_trend",
    "vw_looker_audit_rejection_reasons",
    "vw_looker_audit_ats_health",
    "vw_looker_audit_companies",
    "vw_looker_audit_jobs",
]


def upgrade() -> None:
    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_overview AS
            SELECT
                NOW() AS generated_at,
                metrics.jobs_total,
                metrics.jobs_24h,
                metrics.companies_total,
                metrics.companies_24h,
                metrics.company_ats_total,
                metrics.company_ats_24h,
                metrics.last_tick_at,
                company_activity.last_active_job_at,
                window_7d.approved_7d,
                window_7d.review_7d,
                window_7d.rejected_7d,
                window_7d.approved_ratio_7d,
                ats_health.ats_health_count
            FROM (
                SELECT
                    (SELECT COUNT(*)::bigint FROM jobs) AS jobs_total,
                    (SELECT COUNT(*)::bigint FROM jobs WHERE first_seen_at >= NOW() - INTERVAL '24 hours') AS jobs_24h,
                    (SELECT COUNT(*)::bigint FROM companies) AS companies_total,
                    (SELECT COUNT(*)::bigint FROM companies WHERE created_at >= NOW() - INTERVAL '24 hours') AS companies_24h,
                    (SELECT COUNT(*)::bigint FROM company_ats) AS company_ats_total,
                    (SELECT COUNT(*)::bigint FROM company_ats WHERE created_at >= NOW() - INTERVAL '24 hours') AS company_ats_24h,
                    (SELECT MAX(last_seen_at) FROM jobs) AS last_tick_at
            ) AS metrics
            CROSS JOIN (
                SELECT MAX(last_active_job_at) AS last_active_job_at
                FROM companies
            ) AS company_activity
            CROSS JOIN (
                SELECT
                    COUNT(*) FILTER (WHERE compliance_status = 'approved')::bigint AS approved_7d,
                    COUNT(*) FILTER (WHERE compliance_status = 'review')::bigint AS review_7d,
                    COUNT(*) FILTER (WHERE compliance_status = 'rejected')::bigint AS rejected_7d,
                    ROUND(
                        COUNT(*) FILTER (WHERE compliance_status = 'approved')::numeric
                        / NULLIF(COUNT(*), 0) * 100,
                        2
                    ) AS approved_ratio_7d
                FROM jobs
                WHERE first_seen_at > NOW() - INTERVAL '7 days'
            ) AS window_7d
            CROSS JOIN (
                SELECT COUNT(*)::bigint AS ats_health_count
                FROM company_ats ca
                JOIN companies c ON c.company_id = ca.company_id
                WHERE ca.is_active = TRUE
                  AND c.is_active = TRUE
                  AND (
                      ca.last_sync_at < NOW() - INTERVAL '3 days'
                      OR (ca.last_sync_at IS NULL AND ca.created_at < NOW() - INTERVAL '3 days')
                  )
            ) AS ats_health
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_company_stats AS
            SELECT
                c.legal_name,
                COUNT(*)::bigint AS total_jobs,
                COUNT(*) FILTER (WHERE j.compliance_status = 'approved')::bigint AS approved,
                COUNT(*) FILTER (WHERE j.compliance_status = 'rejected')::bigint AS rejected,
                ROUND(
                    COUNT(*) FILTER (WHERE j.compliance_status = 'approved')::numeric
                    / NULLIF(COUNT(*), 0) * 100,
                    2
                ) AS approved_ratio_pct
            FROM jobs j
            JOIN companies c ON c.company_id = j.company_id
            GROUP BY c.legal_name
            HAVING COUNT(*) > 10
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_source_7d AS
            SELECT
                js.source,
                COUNT(DISTINCT j.job_id)::bigint AS total_jobs,
                COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'approved')::bigint AS approved,
                COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'rejected')::bigint AS rejected,
                ROUND(
                    COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'approved')::numeric
                    / NULLIF(COUNT(DISTINCT j.job_id), 0) * 100,
                    2
                ) AS approved_ratio_pct
            FROM jobs j
            JOIN job_sources js ON js.job_id = j.job_id
            WHERE j.first_seen_at > NOW() - INTERVAL '7 days'
            GROUP BY js.source
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_source_trend AS
            SELECT
                30::integer AS window_days,
                DATE_TRUNC('week', j.first_seen_at)::date AS week_start,
                js.source,
                COUNT(DISTINCT j.job_id)::bigint AS total,
                COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'approved')::bigint AS approved,
                COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'rejected')::bigint AS rejected,
                ROUND(
                    COUNT(DISTINCT j.job_id) FILTER (WHERE j.compliance_status = 'approved')::numeric
                    / NULLIF(COUNT(DISTINCT j.job_id), 0) * 100,
                    1
                ) AS approved_ratio_pct
            FROM jobs j
            JOIN job_sources js ON js.job_id = j.job_id
            WHERE j.first_seen_at > NOW() - INTERVAL '30 days'
              AND j.compliance_status IS NOT NULL
            GROUP BY DATE_TRUNC('week', j.first_seen_at)::date, js.source
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_rejection_reasons AS
            SELECT
                30::integer AS window_days,
                js.source,
                CASE
                    WHEN cr.hard_geo_flag = TRUE THEN 'hard_geo'
                    WHEN j.remote_class = 'NON_REMOTE' THEN 'non_remote'
                    WHEN j.geo_class = 'NON_EU' THEN 'non_eu_geo'
                    ELSE 'other'
                END AS reason,
                COUNT(DISTINCT j.job_id)::bigint AS count
            FROM jobs j
            JOIN job_sources js ON js.job_id = j.job_id
            LEFT JOIN compliance_reports cr ON cr.job_id = j.job_id
            WHERE j.compliance_status = 'rejected'
              AND j.first_seen_at > NOW() - INTERVAL '30 days'
            GROUP BY js.source,
                CASE
                    WHEN cr.hard_geo_flag = TRUE THEN 'hard_geo'
                    WHEN j.remote_class = 'NON_REMOTE' THEN 'non_remote'
                    WHEN j.geo_class = 'NON_EU' THEN 'non_eu_geo'
                    ELSE 'other'
                END
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_ats_health AS
            SELECT
                3::integer AS days_threshold,
                ca.company_ats_id,
                c.legal_name,
                ca.provider,
                ca.ats_slug,
                ca.careers_url,
                ca.last_sync_at,
                GREATEST(
                    0,
                    FLOOR(EXTRACT(EPOCH FROM (NOW() - COALESCE(ca.last_sync_at, ca.created_at))) / 86400)
                )::integer AS days_since_sync
            FROM company_ats ca
            JOIN companies c ON c.company_id = ca.company_id
            WHERE ca.is_active = TRUE
              AND c.is_active = TRUE
              AND (
                  ca.last_sync_at < NOW() - INTERVAL '3 days'
                  OR (ca.last_sync_at IS NULL AND ca.created_at < NOW() - INTERVAL '3 days')
              )
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_companies AS
            SELECT
                company_id,
                legal_name,
                brand_name,
                hq_country,
                eu_entity_verified,
                remote_posture,
                ats_provider,
                ats_slug,
                signal_score,
                approved_jobs_count,
                rejected_jobs_count,
                total_jobs_count,
                last_active_job_at,
                is_active,
                created_at
            FROM companies
            ORDER BY
                signal_score DESC NULLS LAST,
                last_active_job_at DESC NULLS LAST,
                created_at DESC,
                company_id ASC
            LIMIT 10000
        """)
    )

    op.execute(
        sa.text("""
            CREATE OR REPLACE VIEW public.vw_looker_audit_jobs AS
            SELECT
                job_id,
                source,
                source_url,
                title,
                company_name,
                remote_scope,
                status,
                remote_class,
                geo_class,
                compliance_status,
                compliance_score,
                first_seen_at,
                last_seen_at,
                source_department
            FROM jobs
            ORDER BY
                last_seen_at DESC NULLS LAST,
                first_seen_at DESC NULLS LAST,
                job_id ASC
            LIMIT 25000
        """)
    )


def downgrade() -> None:
    for view_name in reversed(VIEW_NAMES):
        op.execute(sa.text(f"DROP VIEW IF EXISTS public.{view_name}"))
