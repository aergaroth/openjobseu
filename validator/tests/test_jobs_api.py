import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from datetime import datetime, timezone

from app.main import app
from storage.db_engine import get_engine
from storage.repositories.jobs_repository import upsert_job

client = TestClient(app)
engine = get_engine()


def _make_job(job_id: str, title: str, company: str, description: str = "Some description") -> dict:
    return {
        "job_id": job_id,
        "source": "test_source",
        "source_job_id": job_id,
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": title,
        "company_name": company,
        "description": description,
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "active",
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
    }


def test_list_jobs_with_q_parameter_searches_title_and_company():
    with engine.begin() as conn:
        upsert_job(_make_job("job1", "Senior Backend Engineer", "Acme"), conn=conn)
        upsert_job(_make_job("job2", "Frontend Developer", "Engineer Corp"), conn=conn)
        upsert_job(_make_job("job3", "Data Scientist", "Data Co"), conn=conn)
        upsert_job(_make_job("job4", "Backend Engineer", "Acme"), conn=conn)

    response = client.get("/jobs?q=engineer")
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    items = data["items"]
    
    # Powninny wrócić oferty gdzie "engineer" jest w tytule (job1, job4) lub w nazwie firmy (job2)
    assert len(items) == 3
    matched_ids = [item["job_id"] for item in items]
    assert "job1" in matched_ids
    assert "job2" in matched_ids
    assert "job4" in matched_ids
    assert "job3" not in matched_ids  # Data Scientist w Data Co


def test_list_jobs_with_q_parameter_empty_result():
    with engine.begin() as conn:
        upsert_job(_make_job("job5", "QA Tester", "Quality Inc"), conn=conn)
        
    response = client.get("/jobs?q=astronaut")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0


def test_list_jobs_with_q_and_other_filters():
    with engine.begin() as conn:
        upsert_job(_make_job("job6", "DevOps Engineer", "Acme"), conn=conn)
        upsert_job(_make_job("job7", "DevOps Engineer", "Other Co"), conn=conn)
        
    response = client.get("/jobs?q=devops&company=Acme")
    assert response.status_code == 200
    items = response.json()["items"]
    
    assert len(items) == 1
    assert items[0]["job_id"] == "job6"


def test_list_jobs_with_q_parameter_searches_description_text():
    with engine.begin() as conn:
        upsert_job(_make_job("job8", "Accountant", "Finance Corp", description="Looking for someone with strong Python skills."), conn=conn)
        upsert_job(_make_job("job9", "Accountant", "Finance Corp", description="Excel spreadsheet master needed."), conn=conn)
        
    response = client.get("/jobs?q=python")
    assert response.status_code == 200
    items = response.json()["items"]
    
    assert len(items) == 1
    assert items[0]["job_id"] == "job8"