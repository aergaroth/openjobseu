import pytest
from app.domain.jobs.job_processing import process_ingested_job

def test_job_processing_only_for_approved(monkeypatch):
    # Mock dependencies
    monkeypatch.setattr("app.domain.jobs.job_processing.apply_policy", 
                        lambda job, source: (job, "some_reason"))
    
    # Mock taxonomy
    taxonomy_calls = []
    def fake_classify_taxonomy(title, **kwargs):
        taxonomy_calls.append(title)
        return {"job_category": "engineering"}
    monkeypatch.setattr("app.domain.jobs.job_processing.classify_taxonomy", fake_classify_taxonomy)

    # Mock salary
    salary_calls = []
    def fake_extract_salary(desc):
        salary_calls.append(desc)
        return {"salary_min": 1000}
    monkeypatch.setattr("app.domain.jobs.job_processing.extract_salary", fake_extract_salary)
    monkeypatch.setattr("app.domain.jobs.job_processing.extract_structured_salary", lambda job: None)
    monkeypatch.setattr("app.domain.jobs.job_processing.detect_salary_transparency", lambda desc, detected: "transparent")
    monkeypatch.setattr("app.domain.jobs.job_processing.compute_job_quality_score", lambda job: 50)

    base_job = {
        "title": "Software Engineer",
        "description": "Building stuff",
        "remote_scope": "EU",
        "company_name": "Acme",
        "company_id": "c1"
    }

    # Case 1: Approved
    job_approved = base_job.copy()
    job_approved["_compliance"] = {"compliance_status": "approved", "remote_model": "remote", "geo_class": "eu"}
    
    processed_approved, report = process_ingested_job(job_approved, source="s1")
    
    assert processed_approved is not None
    assert "job_category" in processed_approved
    assert "salary_min" in processed_approved
    assert len(taxonomy_calls) == 1
    assert len(salary_calls) == 1
    assert report["final_status"] == "approved"

    # Case 2: Rejected
    taxonomy_calls.clear()
    salary_calls.clear()
    job_rejected = base_job.copy()
    job_rejected["_compliance"] = {"compliance_status": "rejected", "remote_model": "remote", "geo_class": "eu"}
    
    processed_rejected, report_rej = process_ingested_job(job_rejected, source="s1")
    
    assert processed_rejected is None
    assert len(taxonomy_calls) == 0
    assert len(salary_calls) == 0
    assert report_rej["final_status"] == "rejected"
