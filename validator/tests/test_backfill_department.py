import pytest
import uuid
from sqlalchemy import text
from fastapi.testclient import TestClient

from app.main import app
from app.utils import backfill_department
from app.utils.backfill_department import backfill_missing_departments
from storage.db_engine import get_engine

client = TestClient(app)

def test_backfill_missing_departments(monkeypatch):
    engine = get_engine()
    company_id = str(uuid.uuid4())
    
    # Przygotowanie danych w testowej bazie
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO companies (company_id, legal_name, ats_provider, ats_slug, is_active, hq_country, remote_posture, created_at, updated_at) 
                VALUES (:company_id, 'Dept Co', 'dummy_ats', 'dept-co', true, 'ZZ', 'UNKNOWN', NOW(), NOW()) 
                ON CONFLICT DO NOTHING
            """),
            {"company_id": company_id}
        )
        conn.execute(
            text("""
                INSERT INTO jobs (job_id, job_uid, job_fingerprint, title, description, source, source_job_id, source_department, company_id, first_seen_at)
                VALUES 
                ('job_dept_1', 'uid_dept_1', 'fp_dept_1', 'Backend Engineer', 'desc', 'dummy_ats:dept-co', 'src_1', NULL, :company_id, NOW()),
                ('job_dept_2', 'uid_dept_2', 'fp_dept_2', 'Frontend', 'desc', 'dummy_ats:dept-co', 'src_2', 'Already Set', :company_id, NOW())
                ON CONFLICT DO NOTHING
            """),
            {"company_id": company_id}
        )

    monkeypatch.setattr(
        backfill_department, 
        "load_active_ats_companies", 
        lambda conn: [{"company_id": company_id, "provider": "dummy_ats", "ats_slug": "dept-co"}]
    )

    class DummyAdapter:
        def fetch(self, company, updated_since=None):
            return [{"id": "src_1", "dept": "Engineering"}, {"id": "src_2", "dept": "IT"}]
        def normalize(self, raw_job):
            return {"source_job_id": raw_job["id"], "department": raw_job["dept"], "source": "dummy_ats:dept-co"}

    monkeypatch.setattr(backfill_department, "get_adapter", lambda provider: DummyAdapter())

    def mock_process(job, source):
        return {**job, "job_family": "software_development"}, {}

    monkeypatch.setattr(backfill_department, "process_ingested_job", mock_process)

    updated = backfill_missing_departments()
    assert updated == 1
    
    with engine.connect() as conn:
        row = conn.execute(text("SELECT source_department, job_family FROM jobs WHERE job_id = 'job_dept_1'")).mappings().one()
        assert row["source_department"] == "Engineering"
        assert row["job_family"] == "software_development"

def test_backfill_department_endpoint(monkeypatch):
    monkeypatch.setattr("app.api.system.backfill_missing_departments", lambda: 5)
    response = client.post("/internal/backfill-department")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "updated_jobs_count": 5}