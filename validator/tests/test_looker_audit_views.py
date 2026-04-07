import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from storage.db_engine import get_engine


engine = get_engine()


def _insert_company(
    conn,
    *,
    legal_name: str,
    signal_score: int,
    approved_jobs_count: int,
    rejected_jobs_count: int,
    total_jobs_count: int,
    last_active_job_at: datetime | None,
) -> str:
    company_id = str(uuid.uuid4())
    conn.execute(
        text("""
            INSERT INTO companies (
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
                created_at,
                updated_at
            )
            VALUES (
                :company_id,
                :legal_name,
                :brand_name,
                'PL',
                TRUE,
                'REMOTE_ONLY',
                'greenhouse',
                :ats_slug,
                :signal_score,
                :approved_jobs_count,
                :rejected_jobs_count,
                :total_jobs_count,
                :last_active_job_at,
                TRUE,
                :created_at,
                :updated_at
            )
        """),
        {
            "company_id": company_id,
            "legal_name": legal_name,
            "brand_name": legal_name,
            "ats_slug": legal_name.lower().replace(" ", "-"),
            "signal_score": int(signal_score),
            "approved_jobs_count": int(approved_jobs_count),
            "rejected_jobs_count": int(rejected_jobs_count),
            "total_jobs_count": int(total_jobs_count),
            "last_active_job_at": last_active_job_at,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
    )
    return company_id


def _insert_company_ats(
    conn,
    *,
    company_id: str,
    provider: str,
    ats_slug: str,
    careers_url: str,
    created_at: datetime,
    last_sync_at: datetime | None,
) -> None:
    conn.execute(
        text("""
            INSERT INTO company_ats (
                company_ats_id,
                company_id,
                provider,
                ats_slug,
                careers_url,
                is_active,
                created_at,
                updated_at,
                last_sync_at
            )
            VALUES (
                :company_ats_id,
                :company_id,
                :provider,
                :ats_slug,
                :careers_url,
                TRUE,
                :created_at,
                :updated_at,
                :last_sync_at
            )
        """),
        {
            "company_ats_id": str(uuid.uuid4()),
            "company_id": company_id,
            "provider": provider,
            "ats_slug": ats_slug,
            "careers_url": careers_url,
            "created_at": created_at,
            "updated_at": datetime.now(timezone.utc),
            "last_sync_at": last_sync_at,
        },
    )


def _insert_job(
    conn,
    *,
    job_id: str,
    company_id: str,
    company_name: str,
    source: str,
    title: str,
    first_seen_at: datetime,
    last_seen_at: datetime,
    compliance_status: str,
    compliance_score: int,
    remote_class: str,
    geo_class: str,
) -> None:
    conn.execute(
        text("""
            INSERT INTO jobs (
                job_id,
                source,
                source_job_id,
                source_url,
                title,
                company_name,
                description,
                remote_source_flag,
                remote_scope,
                status,
                first_seen_at,
                last_seen_at,
                remote_class,
                geo_class,
                compliance_status,
                compliance_score,
                company_id,
                job_uid,
                job_fingerprint,
                source_department
            )
            VALUES (
                :job_id,
                :source,
                :source_job_id,
                :source_url,
                :title,
                :company_name,
                'Role description',
                TRUE,
                'EU-wide',
                'active',
                :first_seen_at,
                :last_seen_at,
                :remote_class,
                :geo_class,
                :compliance_status,
                :compliance_score,
                :company_id,
                :job_uid,
                :job_fingerprint,
                'Engineering'
            )
        """),
        {
            "job_id": job_id,
            "source": source,
            "source_job_id": job_id,
            "source_url": f"https://example.com/jobs/{job_id}",
            "title": title,
            "company_name": company_name,
            "first_seen_at": first_seen_at,
            "last_seen_at": last_seen_at,
            "remote_class": remote_class,
            "geo_class": geo_class,
            "compliance_status": compliance_status,
            "compliance_score": int(compliance_score),
            "company_id": company_id,
            "job_uid": f"uid-{job_id}",
            "job_fingerprint": f"fp-{job_id}",
        },
    )

    conn.execute(
        text("""
            INSERT INTO job_sources (
                job_id,
                source,
                source_job_id,
                source_url,
                first_seen_at,
                last_seen_at,
                created_at,
                updated_at,
                seen_count
            )
            VALUES (
                :job_id,
                :source,
                :source_job_id,
                :source_url,
                :first_seen_at,
                :last_seen_at,
                :created_at,
                :updated_at,
                1
            )
        """),
        {
            "job_id": job_id,
            "source": source,
            "source_job_id": job_id,
            "source_url": f"https://example.com/jobs/{job_id}",
            "first_seen_at": first_seen_at,
            "last_seen_at": last_seen_at,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
    )


def _insert_compliance_report(conn, *, job_id: str, hard_geo_flag: bool) -> None:
    conn.execute(
        text("""
            INSERT INTO compliance_reports (
                report_id,
                job_id,
                policy_version,
                hard_geo_flag,
                final_score,
                final_status,
                created_at,
                job_uid
            )
            VALUES (
                :report_id,
                :job_id,
                'v2',
                :hard_geo_flag,
                0,
                'rejected',
                :created_at,
                :job_uid
            )
        """),
        {
            "report_id": str(uuid.uuid4()),
            "job_id": job_id,
            "hard_geo_flag": bool(hard_geo_flag),
            "created_at": datetime.now(timezone.utc),
            "job_uid": f"uid-{job_id}",
        },
    )


def test_looker_views_exist():
    expected = {
        "vw_looker_audit_overview",
        "vw_looker_audit_company_stats",
        "vw_looker_audit_source_7d",
        "vw_looker_audit_source_trend",
        "vw_looker_audit_rejection_reasons",
        "vw_looker_audit_ats_health",
        "vw_looker_audit_companies",
        "vw_looker_audit_jobs",
    }

    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT viewname
                FROM pg_views
                WHERE schemaname = 'public'
                  AND viewname LIKE 'vw_looker_audit_%'
            """)
            )
            .mappings()
            .all()
        )

    assert {row["viewname"] for row in rows} == expected


def test_looker_views_use_looker_friendly_types():
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND (
                      (table_name = 'vw_looker_audit_overview' AND column_name = 'approved_ratio_7d')
                      OR (table_name = 'vw_looker_audit_companies' AND column_name = 'is_active')
                      OR (table_name = 'vw_looker_audit_company_stats' AND column_name = 'approved_ratio_pct')
                  )
                ORDER BY table_name, column_name
            """)
            )
            .mappings()
            .all()
        )

    actual = {(row["table_name"], row["column_name"]): row["data_type"] for row in rows}
    assert actual[("vw_looker_audit_overview", "approved_ratio_7d")] == "numeric"
    assert actual[("vw_looker_audit_companies", "is_active")] == "boolean"
    assert actual[("vw_looker_audit_company_stats", "approved_ratio_pct")] == "numeric"


def test_looker_views_match_expected_audit_metrics():
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        company_a = _insert_company(
            conn,
            legal_name="Looker Company A",
            signal_score=40,
            approved_jobs_count=8,
            rejected_jobs_count=3,
            total_jobs_count=11,
            last_active_job_at=now - timedelta(hours=1),
        )
        company_b = _insert_company(
            conn,
            legal_name="Looker Company B",
            signal_score=90,
            approved_jobs_count=0,
            rejected_jobs_count=0,
            total_jobs_count=0,
            last_active_job_at=now - timedelta(days=1),
        )

        _insert_company_ats(
            conn,
            company_id=company_a,
            provider="greenhouse",
            ats_slug="looker-company-a",
            careers_url="https://example.com/a/careers",
            created_at=now - timedelta(days=6),
            last_sync_at=now - timedelta(days=5),
        )
        _insert_company_ats(
            conn,
            company_id=company_b,
            provider="lever",
            ats_slug="looker-company-b",
            careers_url="https://example.com/b/careers",
            created_at=now - timedelta(days=2),
            last_sync_at=now - timedelta(hours=6),
        )

        for idx in range(8):
            _insert_job(
                conn,
                job_id=f"looker-approved-{idx}",
                company_id=company_a,
                company_name="Looker Company A",
                source="greenhouse:alpha",
                title=f"Approved Role {idx}",
                first_seen_at=now - timedelta(days=1),
                last_seen_at=now - timedelta(minutes=idx),
                compliance_status="approved",
                compliance_score=95,
                remote_class="REMOTE_ONLY",
                geo_class="EU_REGION",
            )

        for idx in range(3):
            job_id = f"looker-rejected-{idx}"
            _insert_job(
                conn,
                job_id=job_id,
                company_id=company_a,
                company_name="Looker Company A",
                source="lever:beta",
                title=f"Rejected Role {idx}",
                first_seen_at=now - timedelta(days=2),
                last_seen_at=now - timedelta(hours=idx + 1),
                compliance_status="rejected",
                compliance_score=0,
                remote_class="NON_REMOTE",
                geo_class="NON_EU",
            )
            _insert_compliance_report(conn, job_id=job_id, hard_geo_flag=(idx == 0))

    with engine.connect() as conn:
        overview = conn.execute(text("SELECT * FROM public.vw_looker_audit_overview")).mappings().one()
        company_stats = (
            conn.execute(
                text("""
                SELECT *
                FROM public.vw_looker_audit_company_stats
                WHERE legal_name = 'Looker Company A'
            """)
            )
            .mappings()
            .one()
        )
        source_7d = (
            conn.execute(
                text("""
                SELECT source, total_jobs, approved, rejected
                FROM public.vw_looker_audit_source_7d
                ORDER BY source
            """)
            )
            .mappings()
            .all()
        )
        source_trend = (
            conn.execute(
                text("""
                SELECT source, total, approved, rejected
                FROM public.vw_looker_audit_source_trend
                ORDER BY source
            """)
            )
            .mappings()
            .all()
        )
        rejection_reasons = (
            conn.execute(
                text("""
                SELECT source, reason, count
                FROM public.vw_looker_audit_rejection_reasons
                WHERE source = 'lever:beta'
                ORDER BY reason
            """)
            )
            .mappings()
            .all()
        )
        ats_health = (
            conn.execute(
                text("""
                SELECT legal_name, provider, days_threshold, days_since_sync
                FROM public.vw_looker_audit_ats_health
                ORDER BY days_since_sync DESC
            """)
            )
            .mappings()
            .all()
        )
        company_drilldown = (
            conn.execute(
                text("""
                SELECT legal_name, is_active
                FROM public.vw_looker_audit_companies
                LIMIT 2
            """)
            )
            .mappings()
            .all()
        )
        jobs_drilldown = (
            conn.execute(
                text("""
                SELECT job_id
                FROM public.vw_looker_audit_jobs
                LIMIT 1
            """)
            )
            .mappings()
            .one()
        )

    assert overview["jobs_total"] == 11
    assert overview["companies_total"] == 2
    assert overview["company_ats_total"] == 2
    assert overview["approved_7d"] == 8
    assert overview["rejected_7d"] == 3
    assert overview["ats_health_count"] == 1

    assert company_stats["total_jobs"] == 11
    assert company_stats["approved"] == 8
    assert company_stats["rejected"] == 3
    assert float(company_stats["approved_ratio_pct"]) == 72.73

    assert source_7d == [
        {"source": "greenhouse:alpha", "total_jobs": 8, "approved": 8, "rejected": 0},
        {"source": "lever:beta", "total_jobs": 3, "approved": 0, "rejected": 3},
    ]

    assert source_trend == [
        {"source": "greenhouse:alpha", "total": 8, "approved": 8, "rejected": 0},
        {"source": "lever:beta", "total": 3, "approved": 0, "rejected": 3},
    ]

    assert rejection_reasons == [
        {"source": "lever:beta", "reason": "hard_geo", "count": 1},
        {"source": "lever:beta", "reason": "non_remote", "count": 2},
    ]

    assert len(ats_health) == 1
    assert ats_health[0]["legal_name"] == "Looker Company A"
    assert ats_health[0]["provider"] == "greenhouse"
    assert ats_health[0]["days_threshold"] == 3
    assert ats_health[0]["days_since_sync"] >= 5

    assert company_drilldown[0]["legal_name"] == "Looker Company B"
    assert company_drilldown[0]["is_active"] is True
    assert jobs_drilldown["job_id"] == "looker-approved-0"
