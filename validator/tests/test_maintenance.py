import uuid
from sqlalchemy import text
from storage.db_engine import get_engine
from app.workers.maintenance import run_maintenance_pipeline


def test_maintenance_pipeline_updates_company_stats(clean_db):
    engine = get_engine()
    
    comp1_id = str(uuid.uuid4())
    comp2_id = str(uuid.uuid4())

    with engine.begin() as conn:
        # Insert dummy companies
        conn.execute(text("""
            INSERT INTO companies (company_id, legal_name, bootstrap, is_active, hq_country, remote_posture, eu_entity_verified, created_at, updated_at)
            VALUES 
            (:comp1_id, 'Acme EU', true, true, 'PL', 'REMOTE_ONLY', true, NOW(), NOW()),
            (:comp2_id, 'Acme US', true, true, 'US', 'UNKNOWN', false, NOW(), NOW())
        """), {"comp1_id": comp1_id, "comp2_id": comp2_id})
        
        # Insert mixed jobs
        conn.execute(text("""
            INSERT INTO jobs (job_id, job_uid, job_fingerprint, source, source_job_id, company_id, title, status, compliance_status, salary_transparency_status, first_seen_at)
            VALUES 
            ('job-1', 'uid-1', 'fp-1', 'test', 'sj-1', :comp1_id, 'Engineer 1', 'active', 'approved', 'disclosed', '2023-01-01T10:00:00Z'),
            ('job-2', 'uid-2', 'fp-2', 'test', 'sj-2', :comp1_id, 'Engineer 2', 'active', 'approved', 'disclosed', '2023-01-02T10:00:00Z'),
            ('job-3', 'uid-3', 'fp-3', 'test', 'sj-3', :comp1_id, 'Engineer 3', 'active', 'rejected', 'disclosed', '2023-01-03T10:00:00Z'),
            ('job-4', 'uid-4', 'fp-4', 'test', 'sj-4', :comp1_id, 'Engineer 4', 'stale', NULL, 'unknown', '2023-01-04T10:00:00Z'),
            ('job-5', 'uid-5', 'fp-5', 'test', 'sj-5', :comp2_id, 'US Eng', 'active', 'approved', 'unknown', '2023-01-05T10:00:00Z')
        """), {"comp1_id": comp1_id, "comp2_id": comp2_id})
        
    result = run_maintenance_pipeline()
    
    assert result["metrics"]["status"] == "ok", f"Pipeline failed: {result['metrics'].get('error')}"
    assert result["metrics"]["job_stats_updated"] == 2
    assert result["metrics"]["scores_updated"] == 2
    
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT company_id, approved_jobs_count, rejected_jobs_count, total_jobs_count, last_active_job_at, signal_score FROM companies ORDER BY legal_name")).mappings().all()
        
        # comp-1: 2 approved jobs. 
        # Score = (PL (+20) + REMOTE_ONLY (+40) + EU entity (+25) + ratio 2/4=0.5 (+8)) = 93
        # Transparency ratio 3/4 = 0.75 >= 0.5 -> Multiplier 1.2 -> 93 * 1.2 = 111.6 -> 112
        assert str(rows[0]["company_id"]) == comp1_id
        assert rows[0]["total_jobs_count"] == 4
        assert rows[0]["approved_jobs_count"] == 2
        assert rows[0]["rejected_jobs_count"] == 1
        assert str(rows[0]["last_active_job_at"]).startswith("2023-01-03")
        assert rows[0]["signal_score"] == 112

        # comp-2: 1 approved job.
        # Score = US (+0) + UNKNOWN (+0) + No EU entity (+0) + ratio 1/1=1.0 (+15) = 15
        assert str(rows[1]["company_id"]) == comp2_id
        assert rows[1]["total_jobs_count"] == 1
        assert rows[1]["approved_jobs_count"] == 1
        assert rows[1]["rejected_jobs_count"] == 0
        assert str(rows[1]["last_active_job_at"]).startswith("2023-01-05")
        assert rows[1]["signal_score"] == 15