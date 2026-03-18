from enum import Enum
import pytest
from app.domain.jobs.job_processing import process_ingested_job, _string_like


class DummyEnum(Enum):
    TEST_VAL = "test_val"


def test_string_like():
    assert _string_like(None) is None
    assert _string_like("hello") == "hello"
    assert _string_like(DummyEnum.TEST_VAL) == "test_val"
    assert _string_like(123) == "123"


def test_job_processing_handles_approved_and_rejected(monkeypatch):
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
    def fake_extract_salary(desc, title=None):
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
    
    assert processed_rejected is not None
    assert "job_category" in processed_rejected
    assert "salary_min" in processed_rejected
    assert len(taxonomy_calls) == 1
    assert len(salary_calls) == 1
    assert report_rej["final_status"] == "rejected"


def test_job_processing_identity_generation(monkeypatch):
    monkeypatch.setattr("app.domain.jobs.job_processing.apply_policy", lambda job, source: (job, None))
    monkeypatch.setattr("app.domain.jobs.job_processing.classify_taxonomy", lambda **kwargs: {})
    monkeypatch.setattr("app.domain.jobs.job_processing.extract_structured_salary", lambda job: None)
    monkeypatch.setattr("app.domain.jobs.job_processing.extract_salary", lambda desc, title=None: None)
    monkeypatch.setattr("app.domain.jobs.job_processing.detect_salary_transparency", lambda desc, detected: "unknown")
    monkeypatch.setattr("app.domain.jobs.job_processing.compute_job_quality_score", lambda job: 50)
    
    job = {
        "title": "Backend", 
        "description": "Desc", 
        "company_id": "c1",
        "remote_scope": "EU",
        "company_name": "Acme",
        "source": "test_src",
        "source_job_id": "42",
        "_compliance": {}
    }
    
    processed, _ = process_ingested_job(job, "test")
    
    assert processed is not None
    # Sprawdzamy czy identyfikatory zostały wygenerowane i wstrzyknięte do oferty
    assert "job_id" in processed
    assert "job_uid" in processed
    assert "job_fingerprint" in processed
    
    # Weryfikujemy czy proces na samym końcu znormalizował puste klasy polityki do wartości typu 'unknown'
    assert processed["remote_class"] == "unknown"
    assert processed["geo_class"] == "unknown"


def test_job_processing_early_exit_on_none_job(monkeypatch):
    monkeypatch.setattr("app.domain.jobs.job_processing.apply_policy", lambda job, source: (None, "hard_reject"))
    
    base_job = {
        "title": "Software Engineer",
        "remote_scope": "EU",
        "company_name": "Acme",
        "company_id": "c1",
        "_compliance": {
            "policy_version": "v1",
            "remote_model": "remote",
            "geo_class": "eu",
            "compliance_score": 0,
            "compliance_status": "rejected",
            "decision_trace": [],
            "policy_reason": "hard_reject"
        }
    }
    
    processed, report = process_ingested_job(base_job, "test")
    
    # Skoro odrzucono stanowisko bezpośrednio na etapie apply_policy, otrzymujemy None dla job 
    # i pełny raport odrzucenia (aby móc zalogować to w metrykach audytowych)
    assert processed is None
    assert report["final_status"] == "rejected"
    assert report["policy_reason"] == "hard_reject"


def test_job_processing_salary_parsing_low_confidence(monkeypatch):
    monkeypatch.setattr("app.domain.jobs.job_processing.apply_policy", lambda job, source: (job, None))
    monkeypatch.setattr("app.domain.jobs.job_processing.classify_taxonomy", lambda **kwargs: {})
    monkeypatch.setattr("app.domain.jobs.job_processing.extract_structured_salary", lambda job: None)
    
    def fake_extract_salary(desc, title=None):
        # Symulacja parsera zwracającego słaby poziom pewności (<80)
        return {"salary_min": 1000, "salary_confidence": 75}
        
    monkeypatch.setattr("app.domain.jobs.job_processing.extract_salary", fake_extract_salary)
    monkeypatch.setattr("app.domain.jobs.job_processing.detect_salary_transparency", lambda desc, detected: "disclosed")
    monkeypatch.setattr("app.domain.jobs.job_processing.compute_job_quality_score", lambda job: 50)
    
    job = {"title": "A", "description": "B", "company_id": "c1"}
    
    processed, _ = process_ingested_job(job, "test")
    
    assert processed is not None
    # Oferta powinna zostać otagowana do ręcznego przeglądu/audytu widłami poniżej zaufania
    assert "_salary_parsing_case" in processed
    assert processed["_salary_parsing_case"]["salary_confidence"] == 75
    assert processed["salary_transparency_status"] == "disclosed"
    assert processed["salary_min"] == 1000
