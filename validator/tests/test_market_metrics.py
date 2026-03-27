from unittest.mock import patch

from app.workers.market_metrics import run_market_metrics_worker


def test_run_market_metrics_worker_success():
    """Test poprawnego działania workera market_metrics."""
    with (
        patch("app.workers.market_metrics.compute_market_stats") as mock_compute_stats,
        patch("app.workers.market_metrics.insert_market_daily_stats") as mock_insert_stats,
        patch("app.workers.market_metrics.compute_market_segments") as mock_compute_segments,
        patch("app.workers.market_metrics.insert_market_segments") as mock_insert_segments,
    ):
        mock_compute_stats.return_value = {
            "jobs_created": 2,
            "jobs_expired": 0,
            "jobs_active": 2,
            "jobs_reposted": 0,
        }
        mock_compute_segments.return_value = [{"segment": "tech", "count": 2}]

        result = run_market_metrics_worker()

        assert result["actions"] == ["market_metrics_updated"]
        assert result["metrics"]["component"] == "market_metrics"
        assert result["metrics"]["status"] == "ok"
        assert result["metrics"]["jobs_created"] == 2
        assert result["metrics"]["jobs_expired"] == 0
        assert result["metrics"]["jobs_active"] == 2
        assert result["metrics"]["jobs_reposted"] == 0
        assert result["metrics"]["segments_count"] == 1
        mock_compute_stats.assert_called_once()
        mock_insert_stats.assert_called_once()
        mock_compute_segments.assert_called_once()
        mock_insert_segments.assert_called_once()


def test_run_market_metrics_worker_error():
    """Test obsługi błędu w workerze market_metrics."""
    with patch("app.workers.market_metrics.compute_market_stats") as mock_compute_stats:
        mock_compute_stats.side_effect = Exception("Database error")

        result = run_market_metrics_worker()

        assert result["actions"] == []
        assert result["metrics"]["component"] == "market_metrics"
        assert result["metrics"]["status"] == "error"
        assert "Database error" in result["metrics"]["error"]


def test_run_market_metrics_worker_empty_data():
    """Test workera market_metrics z pustymi danymi."""
    with (
        patch("app.workers.market_metrics.compute_market_stats") as mock_compute_stats,
        patch("app.workers.market_metrics.insert_market_daily_stats") as mock_insert_stats,
        patch("app.workers.market_metrics.compute_market_segments") as mock_compute_segments,
        patch("app.workers.market_metrics.insert_market_segments") as mock_insert_segments,
    ):
        mock_compute_stats.return_value = {
            "jobs_created": 0,
            "jobs_expired": 0,
            "jobs_active": 0,
            "jobs_reposted": 0,
        }
        mock_compute_segments.return_value = []

        result = run_market_metrics_worker()

        assert result["actions"] == ["market_metrics_updated"]
        assert result["metrics"]["component"] == "market_metrics"
        assert result["metrics"]["status"] == "ok"
        assert result["metrics"]["jobs_created"] == 0
        assert result["metrics"]["jobs_expired"] == 0
        assert result["metrics"]["jobs_active"] == 0
        assert result["metrics"]["jobs_reposted"] == 0
        assert result["metrics"]["segments_count"] == 0
        mock_insert_stats.assert_called_once()
        mock_insert_segments.assert_called_once()


def test_run_market_metrics_worker_multiple_segments():
    """Test workera market_metrics z wieloma segmentami."""
    with (
        patch("app.workers.market_metrics.compute_market_stats") as mock_compute_stats,
        patch("app.workers.market_metrics.insert_market_daily_stats") as mock_insert_stats,
        patch("app.workers.market_metrics.compute_market_segments") as mock_compute_segments,
        patch("app.workers.market_metrics.insert_market_segments") as mock_insert_segments,
    ):
        mock_compute_stats.return_value = {
            "jobs_created": 5,
            "jobs_expired": 1,
            "jobs_active": 4,
            "jobs_reposted": 2,
        }
        mock_compute_segments.return_value = [
            {"segment": "tech", "count": 3},
            {"segment": "marketing", "count": 2},
        ]

        result = run_market_metrics_worker()

        assert result["actions"] == ["market_metrics_updated"]
        assert result["metrics"]["component"] == "market_metrics"
        assert result["metrics"]["status"] == "ok"
        assert result["metrics"]["jobs_created"] == 5
        assert result["metrics"]["jobs_expired"] == 1
        assert result["metrics"]["jobs_active"] == 4
        assert result["metrics"]["jobs_reposted"] == 2
        assert result["metrics"]["segments_count"] == 2
        mock_insert_stats.assert_called_once()
        mock_insert_segments.assert_called_once()
