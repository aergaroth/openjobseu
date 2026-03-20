from app.domain.jobs.quality_score import compute_job_quality_score

def test_quality_score_empty_job():
    assert compute_job_quality_score({}) == 0

def test_quality_score_maximum_points():
    job = {
        "seniority": "senior",          # +25
        "specialization": "backend",    # +20
        "salary_min": 15000,            # +15
        "description": "a" * 805,       # +10
        "source": "greenhouse",         # +5
    }
    assert compute_job_quality_score(job) == 75

def test_quality_score_partial_points():
    job = {
        "seniority": "junior",          # +5
        "specialization": "unknown",    # +0
        "description": "short",         # +0
    }
    assert compute_job_quality_score(job) == 5

def test_quality_score_manager_and_frontend():
    job = {
        "seniority": "manager",         # +20
        "specialization": "frontend",   # +20
    }
    assert compute_job_quality_score(job) == 40