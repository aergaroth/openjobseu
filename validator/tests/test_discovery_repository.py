import pytest
import uuid
from sqlalchemy import text

from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    check_ats_exists,
    get_discovered_slugs,
    get_existing_brand_names,
    get_or_create_placeholder_company,
    insert_discovered_slug,
    insert_discovered_company_ats,
    insert_discovered_slugs,
    insert_source_company,
    load_discovery_companies,
    update_discovery_last_checked_at,
    update_discovered_slug_status,
)

engine = get_engine()
pytestmark = pytest.mark.integration_db


def test_insert_source_company():
    with engine.begin() as conn:
        inserted = insert_source_company(conn, "Acme Corp", "https://acme.com/careers")
        assert inserted is True

        # Weryfikacja zapisu w bazie
        row = (
            conn.execute(text("SELECT brand_name, careers_url FROM companies WHERE legal_name = 'Acme Corp'"))
            .mappings()
            .one()
        )
        assert row["brand_name"] == "Acme Corp"
        assert row["careers_url"] == "https://acme.com/careers"


def test_get_existing_brand_names():
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO companies (company_id, brand_name, legal_name, hq_country, remote_posture, created_at, updated_at) 
            VALUES (:id1, 'Apple', 'Apple Inc', 'US', 'UNKNOWN', NOW(), NOW()), 
                   (:id2, 'Banana', 'Banana LLC', 'US', 'UNKNOWN', NOW(), NOW())"""),
            {"id1": str(uuid.uuid4()), "id2": str(uuid.uuid4())},
        )

        names = get_existing_brand_names(conn)
        assert "apple" in names
        assert "banana" in names
        assert "cherry" not in names


def test_get_or_create_placeholder_company():
    with engine.begin() as conn:
        # 1. Stworzenie nowej firmy
        company_id_1 = get_or_create_placeholder_company(conn, "Startup XYZ")
        assert company_id_1 is not None

        # 2. Próba pobrania istniejącej firmy (case-insensitive)
        company_id_2 = get_or_create_placeholder_company(conn, "startup xyz")
        assert company_id_1 == company_id_2


def test_insert_and_check_discovered_company_ats():
    with engine.begin() as conn:
        company_id = get_or_create_placeholder_company(conn, "Test ATS Co")

        # Przed wstawieniem nie powinno być ATS
        assert check_ats_exists(conn, "greenhouse", "test-ats") is False

        # Pierwsze wstawienie
        inserted = insert_discovered_company_ats(
            conn,
            company_id=company_id,
            provider="greenhouse",
            ats_slug="test-ats",
            careers_url="http://test.com/careers",
        )
        assert inserted is True

        # Po wstawieniu
        assert check_ats_exists(conn, "greenhouse", "test-ats") is True

        # Próba wstawienia duplikatu - powinno zignorować i zwrócić False
        # (Zakładając że na tabeli company_ats istnieje unikalny indeks np. uq_company_ats_provider_slug)
        inserted_duplicate = insert_discovered_company_ats(
            conn, company_id=company_id, provider="greenhouse", ats_slug="test-ats"
        )
        assert inserted_duplicate is False


def test_load_and_update_discovery_companies():
    with engine.begin() as conn:
        comp1_id = get_or_create_placeholder_company(conn, "No careers URL")
        comp2_id = get_or_create_placeholder_company(conn, "Has careers URL")
        comp3_id = get_or_create_placeholder_company(conn, "Has ATS already")

        conn.execute(
            text("UPDATE companies SET careers_url = 'http://foo' WHERE company_id = :id"),
            {"id": comp2_id},
        )
        conn.execute(
            text("UPDATE companies SET careers_url = 'http://bar', ats_provider = 'lever' WHERE company_id = :id"),
            {"id": comp3_id},
        )

        # Faza 'careers'
        candidates = load_discovery_companies(conn, phase="careers", limit=10)
        # PostgreSQL i psycopg zwracają obiekty typu uuid.UUID, zamieniamy je na typ str, by móc porówywać
        candidate_ids = [str(c["company_id"]) for c in candidates]

        # Tylko comp2 ma careers_url i nie ma ats_provider
        assert comp2_id in candidate_ids
        assert comp1_id not in candidate_ids
        assert comp3_id not in candidate_ids

        # Test aktualizacji czasu sprawdzenia
        update_discovery_last_checked_at(conn, comp2_id, phase="careers")

        row = (
            conn.execute(
                text("SELECT careers_last_checked_at FROM companies WHERE company_id = :id"),
                {"id": comp2_id},
            )
            .mappings()
            .one()
        )
        assert row["careers_last_checked_at"] is not None


def test_insert_discovered_slugs():
    with engine.begin() as conn:
        # Wyczyść ewentualne stare dane z innych testów dla izolacji (nie usuwamy bo robi to fixtura clean_db, ale można upewnić się, że tabela w ogóle istnieje)
        conn.execute(text("DELETE FROM discovered_slugs;"))

        slugs_to_insert = [
            {"provider": "greenhouse", "slug": "slug-a", "discovery_source": "dorking"},
            {"provider": "lever", "slug": "slug-b", "discovery_source": "dorking"},
        ]

        # Pierwszy insert
        insert_discovered_slugs(conn, slugs_to_insert)

        count = conn.execute(text("SELECT COUNT(*) FROM discovered_slugs")).scalar()
        assert count == 2

        # Próba wstawienia tego samego zestawu + 1 nowy, aby upewnić się że ON CONFLICT działa
        slugs_to_insert.append({"provider": "workable", "slug": "slug-c", "discovery_source": "github"})

        insert_discovered_slugs(conn, slugs_to_insert)

        count_after = conn.execute(text("SELECT COUNT(*) FROM discovered_slugs")).scalar()
        assert count_after == 3

        # Upewniamy się czy weszło z poprawnym source
        row = conn.execute(text("SELECT discovery_source FROM discovered_slugs WHERE slug = 'slug-c'")).mappings().one()
        assert row["discovery_source"] == "github"


def test_insert_discovered_slugs_empty_list():
    with engine.begin() as conn:
        # Pusta tablica nie powinna wykrzaczyć składni SQLAlchemy
        insert_discovered_slugs(conn, [])


def test_insert_single_discovered_slug_returns_id_and_can_update_status():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM discovered_slugs;"))
        inserted_id = insert_discovered_slug(
            conn,
            provider="teamtailor",
            slug="career",
            discovery_source="slug_harvest",
        )
        assert inserted_id is not None

        update_discovered_slug_status(conn, inserted_id, "needs_token")
        row = conn.execute(text("SELECT status FROM discovered_slugs WHERE id = :id"), {"id": inserted_id}).mappings().one()
        assert row["status"] == "needs_token"


def test_get_discovered_slugs_filters_by_provider_and_status():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM discovered_slugs;"))
        conn.execute(
            text("""
                INSERT INTO discovered_slugs (provider, slug, discovery_source, status)
                VALUES
                    ('teamtailor', 'career', 'slug_harvest', 'needs_token'),
                    ('traffit', 'acme-hr', 'slug_harvest', 'pending')
            """)
        )

        teamtailor_rows = get_discovered_slugs(conn, provider="teamtailor", status="needs_token", limit=50)
        assert len(teamtailor_rows) == 1
        assert teamtailor_rows[0]["provider"] == "teamtailor"
        assert teamtailor_rows[0]["status"] == "needs_token"
