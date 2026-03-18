import pytest
import time
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


def test_list_jobs_pagination_structure():
    with engine.begin() as conn:
        upsert_job(_make_job("job_page_1", "Backend", "Acme"), conn=conn)
        upsert_job(_make_job("job_page_2", "Frontend", "Acme"), conn=conn)
        upsert_job(_make_job("job_page_3", "DevOps", "Acme"), conn=conn)

    response = client.get("/jobs?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()

    # Sprawdzamy strukturę kontraktu paginacji
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2


def test_list_jobs_handles_large_volume_and_fuzzy_search():
    # Generujemy 1000 zanonimizowanych ofert + 1 specyficzną do odnalezienia
    jobs_data = []
    for i in range(1000):
        jobs_data.append({
            "job_id": f"vol_{i}",
            "job_uid": f"uid_{i}",
            "job_fingerprint": f"fp_{i}",
            "source": "bulk",
            "source_job_id": str(i),
            "source_url": f"https://example.com/bulk/{i}",
            "title": f"Generic Engineer {i}",
            "company_name": f"Company {i % 50}",
            "description": "Standard boilerplate description for volume testing.",
            "remote_source_flag": True,
            "remote_scope": "Europe",
            "status": "active",
            "first_seen_at": "2026-01-01T00:00:00+00:00",
        })
        
    jobs_data.append({
        "job_id": "vol_target",
        "job_uid": "uid_target",
        "job_fingerprint": "fp_target",
        "source": "bulk",
        "source_job_id": "target",
        "source_url": "https://example.com/target",
        "title": "Unicorn Whisperer",
        "company_name": "Magical Corp",
        "description": "Looking for someone to talk to unicorns.",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "active",
        "first_seen_at": "2026-01-01T00:00:00+00:00",
    })
    
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO jobs (
                    job_id, job_uid, job_fingerprint, source, source_job_id, source_url, title, company_name, 
                    description, remote_source_flag, remote_scope, status, first_seen_at
                ) VALUES (
                    :job_id, :job_uid, :job_fingerprint, :source, :source_job_id, :source_url, :title, :company_name,
                    :description, :remote_source_flag, :remote_scope, :status, :first_seen_at
                )
            """),
            jobs_data
        )
        
    # Test 1: Sprawdzenie samej paginacji na dużej paczce
    start_time = time.perf_counter()
    res_all = client.get("/jobs?limit=50")
    dur_all = time.perf_counter() - start_time
    
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 1001
    assert len(data_all["items"]) == 50
    
    # Test 2: Sprawdzenie fuzzy searchu dla zakopanego wyniku (z pomiarem czasu jako wskaźnikiem wydajności)
    start_search = time.perf_counter()
    res_search = client.get("/jobs?q=unicorn")
    dur_search = time.perf_counter() - start_search
    
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] >= 1
    
    # Unicorn Whisperer powinien znaleźć się na samym szczycie (dystans trigramowy)
    assert data_search["items"][0]["job_id"] == "vol_target"