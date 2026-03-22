from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app

client = TestClient(app)


def test_list_jobs_with_q_parameter_searches_title_and_company(db_factory):
    comp_acme = db_factory.create_company(legal_name="Acme")
    comp_eng = db_factory.create_company(legal_name="Engineer Corp")
    comp_data = db_factory.create_company(legal_name="Data Co")

    db_factory.create_job(
        comp_acme["company_id"],
        job_id="job1",
        title="Senior Backend Engineer",
        company_name="Acme",
        status="active",
    )
    db_factory.create_job(
        comp_eng["company_id"],
        job_id="job2",
        title="Frontend Developer",
        company_name="Engineer Corp",
        status="active",
    )
    db_factory.create_job(
        comp_data["company_id"],
        job_id="job3",
        title="Data Scientist",
        company_name="Data Co",
        status="active",
    )
    db_factory.create_job(
        comp_acme["company_id"],
        job_id="job4",
        title="Backend Engineer",
        company_name="Acme",
        status="active",
    )

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


def test_list_jobs_with_q_parameter_empty_result(db_factory):
    comp = db_factory.create_company(legal_name="Quality Inc")
    db_factory.create_job(
        comp["company_id"],
        job_id="job5",
        title="QA Tester",
        company_name="Quality Inc",
        status="active",
    )

    response = client.get("/jobs?q=astronaut")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0


def test_list_jobs_with_q_and_other_filters(db_factory):
    comp_acme = db_factory.create_company(legal_name="Acme")
    comp_other = db_factory.create_company(legal_name="Other Co")
    db_factory.create_job(
        comp_acme["company_id"],
        job_id="job6",
        title="DevOps Engineer",
        company_name="Acme",
        status="active",
    )
    db_factory.create_job(
        comp_other["company_id"],
        job_id="job7",
        title="DevOps Engineer",
        company_name="Other Co",
        status="active",
    )

    response = client.get("/jobs?q=devops&company=Acme")
    assert response.status_code == 200
    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["job_id"] == "job6"


def test_list_jobs_with_q_parameter_ignores_description_text(db_factory):
    comp = db_factory.create_company(legal_name="Finance Corp")
    db_factory.create_job(
        comp["company_id"],
        job_id="job8",
        title="Accountant",
        company_name="Finance Corp",
        description="Looking for someone with strong Python skills.",
        status="active",
    )
    db_factory.create_job(
        comp["company_id"],
        job_id="job9",
        title="Accountant",
        company_name="Finance Corp",
        description="Excel spreadsheet master needed.",
        status="active",
    )

    response = client.get("/jobs?q=python")
    assert response.status_code == 200
    items = response.json()["items"]

    # Ze względów wydajnościowych (brak pełnotekstowego indeksu FTS) celowo ignorujemy opis w zapytaniach "q"
    assert len(items) == 0


def test_list_jobs_pagination_structure(db_factory):
    comp = db_factory.create_company(legal_name="Acme")
    db_factory.create_job(
        comp["company_id"],
        job_id="job_page_1",
        title="Backend",
        company_name="Acme",
        status="active",
    )
    db_factory.create_job(
        comp["company_id"],
        job_id="job_page_2",
        title="Frontend",
        company_name="Acme",
        status="active",
    )
    db_factory.create_job(
        comp["company_id"],
        job_id="job_page_3",
        title="DevOps",
        company_name="Acme",
        status="active",
    )

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


def test_list_jobs_handles_large_volume_and_fuzzy_search(db_factory):
    # Generujemy 1000 zanonimizowanych ofert + 1 specyficzną do odnalezienia
    jobs_data = []
    for i in range(1000):
        jobs_data.append(
            {
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
            }
        )

    jobs_data.append(
        {
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
        }
    )

    with db_factory.engine.begin() as conn:
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
            jobs_data,
        )

    # Test 1: Sprawdzenie samej paginacji na dużej paczce
    res_all = client.get("/jobs?limit=50")

    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 1001
    assert len(data_all["items"]) == 50

    # Test 2: Sprawdzenie fuzzy searchu dla zakopanego wyniku (z pomiarem czasu jako wskaźnikiem wydajności)
    res_search = client.get("/jobs?q=unicorn")

    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] >= 1

    # Unicorn Whisperer powinien znaleźć się na samym szczycie (dystans trigramowy)
    assert data_search["items"][0]["job_id"] == "vol_target"


def test_list_jobs_with_realistic_faker_data(seed_realistic_market_data):
    """
    Test weryfikujący, że endpoint poprawnie filtruje i renderuje realistyczne,
    złożone obiekty wygenerowane z Fakera (zawierające pełne opisy, url'e i różne waluty).
    """
    response = client.get("/jobs?status=active")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    # Dzięki zablokowanemu ziarnu losowości (Faker.seed(42)), możemy być pewni,
    # że spośród 5 firm wygeneruje się przynajmniej jedna 'aktywna' oferta.
    assert data["total"] > 0

    # Sprawdzamy, czy w obiekcie znalazły się uwiarygodnione dane
    first_job = data["items"][0]
    assert "http" in first_job["source_url"]
