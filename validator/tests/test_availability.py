from app.workers.availability import check_job_availability

TEST_JOBS = [
    {
        "job_id": "ok",
        "source_url": "https://example.com",  # 200
    },
    {
        "job_id": "expired",
        "source_url": "https://example.com/404",  # 404
    },
    {
        "job_id": "timeout",
        "source_url": "http://10.255.255.1",  # timeout
    },
    {
        "job_id": "missing",
        "source_url": None,
    },
]

for job in TEST_JOBS:
    status = check_job_availability(job, timeout=2)
    print(f"{job['job_id']:>8}: {status}")

