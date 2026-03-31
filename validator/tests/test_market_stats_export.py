from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.workers.market_types import DailyStats, MarketStatsResponse
from app.workers.frontend_exporter import (
    _export_charts,
    _export_market_stats,
    run_frontend_export,
)


def _make_stats(n: int = 30) -> list[DailyStats]:
    today = date.today()
    return [
        DailyStats(
            date=today - timedelta(days=n - 1 - i),
            jobs_created=10 + i,
            jobs_expired=5,
            jobs_active=100 + i,
            jobs_reposted=1,
            avg_salary_eur=50000.0 + i * 100,
            median_salary_eur=48000.0 + i * 100,
            remote_ratio=0.5 + i * 0.01,
        )
        for i in range(n)
    ]


def _make_mock_engine(rows):
    """Build a mock SQLAlchemy engine that returns `rows` from execute().mappings().all()."""
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = rows

    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    return mock_engine, mock_conn


# ── _export_market_stats ─────────────────────────────────────────────────────


@patch("app.workers.frontend_exporter.get_engine")
def test_export_market_stats_structure(mock_get_engine):
    stats = _make_stats(30)
    mock_engine, _ = _make_mock_engine([s.model_dump() for s in stats])
    mock_get_engine.return_value = mock_engine
    mock_bucket = MagicMock()

    count, charts_uploaded = _export_market_stats(mock_bucket, "https://cdn.openjobseu.org")

    assert count == 30
    # Last upload_from_string call is the market-stats.json blob
    upload_args, _ = mock_bucket.blob.return_value.upload_from_string.call_args
    response = MarketStatsResponse.model_validate_json(upload_args[0])
    assert response.meta.days_available == 30
    assert response.meta.chart_base_url == "https://cdn.openjobseu.org"
    assert len(response.stats) == 30


@patch("app.workers.frontend_exporter.get_engine")
def test_export_market_stats_empty_table(mock_get_engine):
    mock_engine, _ = _make_mock_engine([])
    mock_get_engine.return_value = mock_engine
    mock_bucket = MagicMock()

    count, charts_uploaded = _export_market_stats(mock_bucket, "https://cdn.openjobseu.org")

    assert count == 0
    # Even with no data, all 6 chart SVGs must be uploaded (flat-line fallback)
    blob_names = [c[0][0] for c in mock_bucket.blob.call_args_list]
    assert "charts/volume-7d.svg" in blob_names
    assert "charts/remote-30d.svg" in blob_names
    assert "market-stats.json" in blob_names

    # Last upload_from_string call is always market-stats.json (str, not SVG bytes)
    last_upload_args = mock_bucket.blob.return_value.upload_from_string.call_args_list[-1][0]
    response = MarketStatsResponse.model_validate_json(last_upload_args[0])
    assert response.stats == []


# ── _export_charts ───────────────────────────────────────────────────────────


def test_export_charts_uploads_six_files():
    mock_bucket = MagicMock()
    uploaded = _export_charts(mock_bucket, _make_stats(30))

    assert uploaded == 6
    blob_names = [c[0][0] for c in mock_bucket.blob.call_args_list]
    for expected in [
        "charts/volume-7d.svg",
        "charts/volume-30d.svg",
        "charts/salary-7d.svg",
        "charts/salary-30d.svg",
        "charts/remote-7d.svg",
        "charts/remote-30d.svg",
    ]:
        assert expected in blob_names, f"{expected} not uploaded"


def test_export_charts_partial_failure():
    call_count = {"n": 0}

    def fail_once(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("GCS upload failed")

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value.upload_from_string.side_effect = fail_once

    uploaded = _export_charts(mock_bucket, _make_stats(30))

    # 5 out of 6 succeed; function must not raise
    assert uploaded == 5


# ── run_frontend_export independence ─────────────────────────────────────────


@patch("app.workers.frontend_exporter._export_market_stats")
@patch("app.workers.frontend_exporter._export_feed")
def test_market_export_independent_of_feed(mock_export_feed, mock_export_market_stats, monkeypatch):
    monkeypatch.setenv("PUBLIC_FEED_BUCKET", "test-bucket")
    monkeypatch.setenv("PUBLIC_FEED_BASE_URL", "https://cdn.example.com")

    mock_export_feed.return_value = (100, 1)
    mock_export_market_stats.side_effect = Exception("market stats exploded")

    with patch("google.cloud.storage.Client"):
        result = run_frontend_export(export_feed=True, export_market_stats=True)

    # Feed succeeded; market stats failure must not surface as an error
    assert result["status"] == "ok"
    assert result["exported_jobs"] == 100
