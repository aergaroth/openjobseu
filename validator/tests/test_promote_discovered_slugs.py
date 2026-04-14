from app.workers.discovery.promote_discovered_slugs import _resolve_company_name


def test_resolve_company_name_prefers_probe_name():
    assert _resolve_company_name({"company_name": "Example Sp. z o.o."}, "example-spzoo") == "Example Sp. z o.o."


def test_resolve_company_name_falls_back_to_slug():
    assert _resolve_company_name({}, "example-company") == "Example Company"


def test_teamtailor_is_not_auto_promoted(monkeypatch):
    """
    Teamtailor discovered slugs are tracked as needs_token instead of being probed/promoted.
    """
    import app.workers.discovery.promote_discovered_slugs as mod

    class DummyConn:
        pass

    class DummyCtx:
        def __enter__(self):
            return DummyConn()

        def __exit__(self, *args):
            pass

    class DummyEngine:
        def connect(self):
            return DummyCtx()

        def begin(self):
            return DummyCtx()

    monkeypatch.setattr(mod, "get_engine", lambda: DummyEngine())
    monkeypatch.setattr(
        mod,
        "get_pending_discovered_slugs",
        lambda conn: [{"id": 1, "provider": "teamtailor", "slug": "career"}],
    )

    calls = {"probe": 0, "status": []}

    def fake_probe(provider, slug):
        calls["probe"] += 1
        return {"jobs_total": 1}

    def fake_update(conn, slug_id, status):
        calls["status"].append((slug_id, status))

    monkeypatch.setattr(mod, "probe_ats", fake_probe)
    monkeypatch.setattr(mod, "update_discovered_slug_status", fake_update)
    monkeypatch.setattr(mod, "insert_discovered_company_ats", lambda *a, **kw: True)
    monkeypatch.setattr(mod, "get_or_create_placeholder_company", lambda *a, **kw: "cid")

    mod.run_promote_discovered_slugs()

    assert calls["probe"] == 0
    assert calls["status"] == [(1, "needs_token")]
