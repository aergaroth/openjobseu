from typing import Dict


def compute_job_quality_score(job: Dict) -> int:
    score = 0

    seniority = job.get("seniority")
    specialization = job.get("specialization")
    description = job.get("description") or ""
    salary = job.get("salary_min")

    # seniority
    if seniority == "senior":
        score += 25
    elif seniority == "manager":
        score += 20
    elif seniority == "junior":
        score += 5

    # specialization (IT roles)
    if specialization in {
        "backend",
        "frontend",
        "fullstack",
        "devops",
        "sre",
        "platform",
        "machine_learning",
    }:
        score += 20

    # salary signal
    if salary:
        score += 15

    # description quality
    if len(description) > 800:
        score += 10

    # ATS quality signal
    if job.get("source") == "greenhouse":
        score += 5

    return score
