import pytest
from app.domain.jobs.enrichment import enrich_and_apply_policy

def test_enrichment_only_for_approved(monkeypatch):
    # Mock dependencies to avoid actual calls
    monkeypatch.setattr("app.domain.jobs.enrichment.apply_policy", 
                        lambda job, source: (job, "some_reason"))
    
    # Mock taxonomy to track calls
    taxonomy_calls = []
    def fake_classify_taxonomy(title):
        taxonomy_calls.append(title)
        return {"job_category": "engineering"}
    monkeypatch.setattr("app.domain.jobs.enrichment.classify_taxonomy", fake_classify_taxonomy)

    # Mock salary to track calls
    salary_calls = []
    def fake_extract_salary(desc):
        salary_calls.append(desc)
        return {"salary_min": 1000}
    monkeypatch.setattr("app.domain.jobs.enrichment.extract_salary", fake_extract_salary)
    monkeypatch.setattr("app.domain.jobs.enrichment.extract_structured_salary", lambda job: None)
    monkeypatch.setattr("app.domain.jobs.enrichment.detect_salary_transparency", lambda desc, detected: "transparent")

    base_job = {
        "title": "Software Engineer",
        "description": "Building stuff",
        "remote_scope": "EU",
        "company_name": "Acme"
    }

    # Case 1: Approved
    job_approved = base_job.copy()
    job_approved["_compliance"] = {"compliance_status": "approved", "remote_model": "remote", "geo_class": "eu"}
    
    enriched_approved, _ = enrich_and_apply_policy(job_approved, raw_job={}, company_id="c1", source="s1")
    
    assert "job_category" in enriched_approved
    assert "salary_min" in enriched_approved
    assert len(taxonomy_calls) == 1
    assert len(salary_calls) == 1

    # Case 2: Rejected
    taxonomy_calls.clear()
    salary_calls.clear()
    job_rejected = base_job.copy()
    job_rejected["_compliance"] = {"compliance_status": "rejected", "remote_model": "remote", "geo_class": "eu"}
    
    enriched_rejected, _ = enrich_and_apply_policy(job_rejected, raw_job={}, company_id="c1", source="s1")
    
    assert "job_category" not in enriched_rejected
    assert "salary_min" not in enriched_rejected
    assert len(taxonomy_calls) == 0
    assert len(salary_calls) == 0
    assert enriched_rejected["salary_transparency_status"] is None
