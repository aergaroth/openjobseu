import pytest

from storage.repositories.market_segments_repository import _normalize_country_rows

pytestmark = pytest.mark.no_db


def _row(value, jobs_active=10, salary_count=0):
    return {
        "segment_value": value,
        "segment_type": "country",
        "jobs_active": jobs_active,
        "jobs_created": 2,
        "salary_count": salary_count,
    }


def test_dedup_removes_plain_when_suffix_remote_variant_exists():
    rows = [_row("Spain"), _row("Spain (Remote)")]
    result = _normalize_country_rows(rows)
    values = [r["segment_value"] for r in result]
    assert "Spain (Remote)" in values
    assert "Spain" not in values


def test_dedup_removes_plain_when_prefix_remote_variant_exists():
    rows = [_row("EMEA"), _row("Remote - EMEA")]
    result = _normalize_country_rows(rows)
    values = [r["segment_value"] for r in result]
    assert "Remote - EMEA" in values
    assert "EMEA" not in values


def test_prefix_remote_wins_over_suffix_remote():
    rows = [_row("Ireland (Remote)"), _row("Remote - Ireland")]
    result = _normalize_country_rows(rows)
    values = [r["segment_value"] for r in result]
    assert "Remote - Ireland" in values
    assert "Ireland (Remote)" not in values


def test_dedup_keeps_plain_when_no_remote_variant():
    rows = [_row("Poland"), _row("Germany (Remote)")]
    result = _normalize_country_rows(rows)
    values = [r["segment_value"] for r in result]
    assert "Poland" in values
    assert "Germany (Remote)" in values


def test_home_based_normalization():
    rows = [_row("Home Based - Ireland")]
    result = _normalize_country_rows(rows)
    assert result[0]["segment_value"] == "Remote - Ireland"


def test_home_based_em_dash_normalization():
    rows = [_row("Home Based – Ireland")]
    result = _normalize_country_rows(rows)
    assert result[0]["segment_value"] == "Remote - Ireland"


def test_excludes_americas():
    rows = [_row("Americas"), _row("LATAM"), _row("APAC"), _row("Asia Pacific"), _row("Germany")]
    result = _normalize_country_rows(rows)
    values = [r["segment_value"] for r in result]
    assert values == ["Germany"]


def test_no_side_effects_on_input():
    rows = [_row("France"), _row("France (Remote)")]
    original_len = len(rows)
    _normalize_country_rows(rows)
    assert len(rows) == original_len


def test_empty_input():
    assert _normalize_country_rows([]) == []


def test_preserves_row_fields_after_normalization():
    row = {
        "segment_value": "Home Based - Sweden",
        "segment_type": "country",
        "jobs_active": 5,
        "jobs_created": 1,
        "salary_count": 2,
    }
    result = _normalize_country_rows([row])
    assert result[0]["jobs_active"] == 5
    assert result[0]["jobs_created"] == 1
    assert result[0]["segment_type"] == "country"
    assert result[0]["salary_count"] == 2


def test_dedup_keeps_salary_count_of_winning_variant():
    rows = [_row("EMEA", jobs_active=52, salary_count=10), _row("Remote - EMEA", jobs_active=83, salary_count=30)]
    result = _normalize_country_rows(rows)
    assert len(result) == 1
    assert result[0]["segment_value"] == "Remote - EMEA"
    assert result[0]["salary_count"] == 30
