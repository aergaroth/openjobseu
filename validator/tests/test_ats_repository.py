import uuid

from sqlalchemy import text

from storage.repositories.ats_repository import (
    deactivate_ats_integration,
    get_ats_integration_by_id,
    load_active_ats_companies,
    mark_ats_synced,
)


def test_load_active_ats_companies_returns_only_active_complete_integrations(db_factory):
    active_company = db_factory.create_company(legal_name="Active Co", is_active=True)
    inactive_company = db_factory.create_company(legal_name="Inactive Co", is_active=False)
    active_id = str(uuid.uuid4())
    inactive_integration_id = str(uuid.uuid4())
    inactive_company_id = str(uuid.uuid4())
    db_factory.create_ats(
        active_company["company_id"],
        company_ats_id=active_id,
        provider="greenhouse",
        ats_slug="active-slug",
    )
    db_factory.create_ats(
        active_company["company_id"],
        company_ats_id=inactive_integration_id,
        provider="lever",
        ats_slug="inactive-integration",
        is_active=False,
    )
    db_factory.create_ats(
        inactive_company["company_id"],
        company_ats_id=inactive_company_id,
        provider="greenhouse",
        ats_slug="inactive-company",
    )

    with db_factory.engine.connect() as conn:
        rows = load_active_ats_companies(conn, limit=20)

    assert [str(row["company_ats_id"]) for row in rows] == [active_id]
    assert rows[0]["legal_name"] == "Active Co"


def test_get_mark_and_deactivate_ats_integration(db_factory):
    company = db_factory.create_company()
    company_ats_id = str(uuid.uuid4())
    ats = db_factory.create_ats(
        company["company_id"],
        company_ats_id=company_ats_id,
        provider="greenhouse",
        ats_slug="acme",
    )

    with db_factory.engine.begin() as conn:
        loaded = get_ats_integration_by_id(conn, ats["company_ats_id"])
        assert str(loaded["company_ats_id"]) == company_ats_id
        assert loaded["ats_provider"] == "greenhouse"

        mark_ats_synced(conn, ats["company_ats_id"], success=True)
        last_sync = conn.execute(
            text("SELECT last_sync_at FROM company_ats WHERE company_ats_id = :company_ats_id"),
            {"company_ats_id": ats["company_ats_id"]},
        ).scalar_one()
        assert last_sync is not None

        mark_ats_synced(conn, ats["company_ats_id"], success=False)
        deactivate_ats_integration(conn, ats["company_ats_id"])
        state = (
            conn.execute(
                text("""
                SELECT is_active, last_sync_at
                FROM company_ats
                WHERE company_ats_id = :company_ats_id
            """),
                {"company_ats_id": ats["company_ats_id"]},
            )
            .mappings()
            .one()
        )

    assert state["is_active"] is False
    assert state["last_sync_at"] is not None


def test_get_ats_integration_by_id_returns_none_for_missing_record(db_factory):
    with db_factory.engine.begin() as conn:
        assert get_ats_integration_by_id(conn, str(uuid.uuid4())) is None
        mark_ats_synced(conn, None, success=True)
