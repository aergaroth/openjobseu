import uuid
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from storage.db_engine import get_engine

client = TestClient(app)
engine = get_engine()


def _insert_company(conn, name: str):
    conn.execute(
        text("""
            INSERT INTO companies (
                company_id, legal_name, brand_name, hq_country, remote_posture, is_active, 
                approved_jobs_count, total_jobs_count, created_at, updated_at
            ) VALUES (
                :id, :name, :name, 'PL', 'UNKNOWN', true, 0, 0, NOW(), NOW()
            )
        """),
        {"id": str(uuid.uuid4()), "name": name},
    )


def test_list_companies_pagination_structure():
    with engine.begin() as conn:
        _insert_company(conn, "Company Alpha")
        _insert_company(conn, "Company Beta")
        _insert_company(conn, "Company Gamma")

    response = client.get("/companies?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()

    assert "cache-control" in response.headers
    assert "max-age=60" in response.headers["cache-control"]

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2
