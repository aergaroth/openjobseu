from scripts.filter_pg_restore_list import filter_restore_list, should_exclude


def test_should_exclude_matches_pg_session_jwt_entries():
    assert should_exclude("123; 0 0 EXTENSION - pg_session_jwt")
    assert should_exclude("124; 0 0 COMMENT - EXTENSION pg_session_jwt")


def test_should_exclude_matches_pgrst_entries():
    assert should_exclude("125; 0 0 SCHEMA - pgrst")
    assert should_exclude("126; 0 0 FUNCTION public pgrst.pre_config()")


def test_should_exclude_ignores_comments_and_unrelated_entries():
    assert not should_exclude("; archive dump list")
    assert not should_exclude("127; 0 0 TABLE public jobs")


def test_filter_restore_list_removes_legacy_entries_only():
    content = (
        "; archive dump list\n"
        "123; 0 0 EXTENSION - pg_session_jwt\n"
        "124; 0 0 COMMENT - EXTENSION pg_session_jwt\n"
        "125; 0 0 SCHEMA - pgrst\n"
        "126; 0 0 FUNCTION public pgrst.pre_config()\n"
        "127; 0 0 TABLE public jobs\n"
        "128; 0 0 TABLE public companies\n"
    )

    filtered, removed = filter_restore_list(content)

    assert removed == 4
    assert "pg_session_jwt" not in filtered
    assert "pgrst" not in filtered
    assert "TABLE public jobs" in filtered
    assert "TABLE public companies" in filtered
