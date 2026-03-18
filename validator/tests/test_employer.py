import unittest
from unittest.mock import MagicMock, patch

from app.domain.taxonomy.enums import RemoteClass
from app.workers.ingestion.employer import ingest_company, run_employer_ingestion


class TestRunEmployerIngestion(unittest.TestCase):
    @patch("app.workers.ingestion.employer.get_engine")
    @patch("app.workers.ingestion.employer.load_active_ats_companies")
    @patch("app.workers.ingestion.employer.ingest_company")
    @patch("app.workers.ingestion.employer.log_ingestion")
    @patch("app.workers.ingestion.employer.perf_counter", side_effect=list(range(1, 100)))
    def test_run_employer_ingestion_happy_path(
        self, mock_perf_counter, mock_log_ingestion, mock_ingest_company, mock_load_companies, mock_get_engine
    ):
        # Arrange
        mock_companies = [{"id": 1}, {"id": 2}]
        mock_load_companies.return_value = mock_companies

        result1 = {
            "fetched": 10,
            "normalized_count": 8,
            "accepted": 7,
            "skipped": 1,
            "rejected_policy_count": 1,
            "rejected_by_reason": {RemoteClass.NON_REMOTE.value: 1, "geo_restriction": 0},
            "remote_model_counts": {
                RemoteClass.REMOTE_ONLY.value: 2,
                "remote_but_geo_restricted": 1,
                RemoteClass.NON_REMOTE.value: 4,
                RemoteClass.UNKNOWN.value: 1,
            },
            "hard_geo_rejected_count": 0,
        }
        result2 = {
            "fetched": 5,
            "normalized_count": 5,
            "accepted": 4,
            "skipped": 0,
            "rejected_policy_count": 1,
            "rejected_by_reason": {RemoteClass.NON_REMOTE.value: 0, "geo_restriction": 1},
            "remote_model_counts": {
                RemoteClass.REMOTE_ONLY.value: 3,
                "remote_but_geo_restricted": 0,
                RemoteClass.NON_REMOTE.value: 1,
                RemoteClass.UNKNOWN.value: 1,
            },
            "hard_geo_rejected_count": 1,
        }
        mock_ingest_company.side_effect = [result1, result2]

        # Act
        result = run_employer_ingestion()

        # Assert
        self.assertEqual(mock_load_companies.call_count, 1)
        self.assertEqual(mock_ingest_company.call_count, 2)

        metrics = result["metrics"]
        self.assertEqual(metrics["status"], "ok")
        self.assertEqual(metrics["companies_processed"], 2)
        self.assertEqual(metrics["companies_failed"], 0)
        self.assertEqual(metrics["synced_ats_count"], 2)
        self.assertEqual(metrics["fetched_count"], 15)
        self.assertEqual(metrics["normalized_count"], 13)
        self.assertEqual(metrics["accepted_count"], 11)
        self.assertEqual(metrics["skipped_count"], 1)
        self.assertEqual(metrics["rejected_policy_count"], 2)
        self.assertEqual(metrics["hard_geo_rejected_count"], 1)

        self.assertEqual(metrics["policy_rejected_by_reason"][RemoteClass.NON_REMOTE.value], 1)
        self.assertEqual(metrics["policy_rejected_by_reason"]["geo_restriction"], 1)

        remote_counts = metrics["remote_model_counts"]
        self.assertEqual(remote_counts[RemoteClass.REMOTE_ONLY.value], 5)
        self.assertEqual(remote_counts["remote_but_geo_restricted"], 1)
        self.assertEqual(remote_counts[RemoteClass.NON_REMOTE.value], 5)
        self.assertEqual(remote_counts[RemoteClass.UNKNOWN.value], 2)

        self.assertEqual(mock_log_ingestion.call_count, 2)

    @patch("app.workers.ingestion.employer.get_engine")
    @patch("app.workers.ingestion.employer.load_active_ats_companies")
    @patch("app.workers.ingestion.employer.ingest_company")
    @patch("app.workers.ingestion.employer.log_ingestion")
    @patch("app.workers.ingestion.employer.perf_counter", side_effect=list(range(1, 100)))
    def test_run_employer_ingestion_with_failures(
        self, mock_perf_counter, mock_log_ingestion, mock_ingest_company, mock_load_companies, mock_get_engine
    ):
        # Arrange
        mock_companies = [{"id": 1}, {"id": 2}, {"id": 3}]
        mock_load_companies.return_value = mock_companies

        result1 = {
            "fetched": 10,
            "normalized_count": 8,
            "accepted": 7,
            "skipped": 1,
            "rejected_policy_count": 1,
            "rejected_by_reason": {RemoteClass.NON_REMOTE.value: 1, "geo_restriction": 0},
            "remote_model_counts": {
                RemoteClass.REMOTE_ONLY.value: 2,
                "remote_but_geo_restricted": 1,
                RemoteClass.NON_REMOTE.value: 4,
                RemoteClass.UNKNOWN.value: 1,
            },
            "hard_geo_rejected_count": 0,
        }
        error_result = {"error": "some_error"}
        slug_error_result = {"error": "invalid_ats_slug"}

        mock_ingest_company.side_effect = [result1, error_result, slug_error_result]

        # Act
        result = run_employer_ingestion()

        # Assert
        self.assertEqual(mock_ingest_company.call_count, 3)

        metrics = result["metrics"]
        self.assertEqual(metrics["status"], "ok")
        self.assertEqual(metrics["companies_processed"], 3)
        self.assertEqual(metrics["companies_failed"], 2)
        self.assertEqual(metrics["companies_invalid_slug"], 1)
        self.assertEqual(metrics["synced_ats_count"], 1)
        self.assertEqual(metrics["fetched_count"], 10)

    @patch("app.workers.ingestion.employer.get_engine")
    @patch("app.workers.ingestion.employer.load_active_ats_companies")
    @patch("app.workers.ingestion.employer.ingest_company")
    @patch("app.workers.ingestion.employer.log_ingestion")
    @patch("app.workers.ingestion.employer.perf_counter", side_effect=list(range(1, 100)))
    def test_run_employer_ingestion_no_companies(
        self, mock_perf_counter, mock_log_ingestion, mock_ingest_company, mock_load_companies, mock_get_engine
    ):
        # Arrange
        mock_load_companies.return_value = []

        # Act
        result = run_employer_ingestion()

        # Assert
        self.assertEqual(mock_ingest_company.call_count, 0)
        metrics = result["metrics"]
        self.assertEqual(metrics["companies_processed"], 0)
        self.assertEqual(metrics["fetched_count"], 0)

    @patch("app.workers.ingestion.employer.get_engine")
    @patch("app.workers.ingestion.employer.load_active_ats_companies")
    @patch("app.workers.ingestion.employer.ingest_company")
    @patch("app.workers.ingestion.employer.log_ingestion")
    @patch("app.workers.ingestion.employer.perf_counter", side_effect=list(range(1, 1000)))
    def test_run_employer_ingestion_stress_with_thread_pool_failures(
        self, mock_perf_counter, mock_log_ingestion, mock_ingest_company, mock_load_companies, mock_get_engine
    ):
        # Arrange: Przygotowujemy 50 firm
        num_companies = 50
        mock_companies = [{"id": i, "ats_slug": f"slug-{i}", "ats_provider": "lever"} for i in range(num_companies)]
        mock_load_companies.return_value = mock_companies

        # Symulujemy awarie z poziomu wątków
        def fake_ingest(company):
            cid = company["id"]
            if cid < 20:
                # Pierwsze 20 firm rzuca brutalnym, nieobsłużonym wyjątkiem w środku ThreadPoolExecutora
                raise RuntimeError(f"Thread pool explosion for company {cid}")
            elif cid < 30:
                # Kolejne 10 firm kończy się standardowym błędem w formacie dict (np. brak odpowiedzi API)
                return {"error": "fetch_failed"}
            else:
                # Ostatnie 20 firm przetwarza się pomyślnie
                return {
                    "fetched": 5,
                    "normalized_count": 5,
                    "accepted": 5,
                    "skipped": 0,
                }

        mock_ingest_company.side_effect = fake_ingest

        # Act
        result = run_employer_ingestion()

        # Assert
        metrics = result["metrics"]
        self.assertEqual(metrics["status"], "ok")
        self.assertEqual(metrics["companies_processed"], 50)
        self.assertEqual(metrics["companies_failed"], 30) # 20 twardych wybuchów + 10 błędów dict
        self.assertEqual(metrics["accepted_jobs"], 100) # 20 firm * 5 ofert = 100

class TestIngestCompany(unittest.TestCase):
    @patch("app.workers.ingestion.employer.get_adapter")
    @patch("app.workers.ingestion.employer.fetch_company_jobs")
    @patch("app.workers.ingestion.employer.get_engine")
    @patch("app.workers.ingestion.employer.process_company_jobs")
    @patch("app.workers.ingestion.employer.mark_ats_synced")
    def test_ingest_company_happy_path(
        self, mock_mark_synced, mock_process, mock_get_engine, mock_fetch, mock_get_adapter
    ):
        # Arrange
        company = {"ats_provider": "test_provider", "company_id": "c1", "company_ats_id": "ats1"}
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        raw_jobs = [{"id": "job1"}]
        mock_fetch.return_value = (raw_jobs, None)
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        # Act
        result = ingest_company(company)

        # Assert
        mock_get_adapter.assert_called_once_with("test_provider")
        mock_fetch.assert_called_once_with(company, mock_adapter, updated_since=None)
        mock_process.assert_called_once()
        metrics_arg = mock_process.call_args.args[5]
        self.assertEqual(metrics_arg.fetched, 1)
        mock_mark_synced.assert_called_once_with(mock_conn, "ats1", success=True)
        self.assertNotIn("error", result)
        self.assertEqual(result["fetched"], 1)

    @patch("app.workers.ingestion.employer.get_adapter", side_effect=ValueError("bad adapter"))
    def test_ingest_company_unsupported_adapter(self, mock_get_adapter):
        # Arrange
        company = {"ats_provider": "bad_provider"}

        # Act
        result = ingest_company(company)

        # Assert
        self.assertEqual(result["error"], "unsupported_ats_provider")
        self.assertEqual(result["fetched"], 0)

    @patch("app.workers.ingestion.employer.get_adapter")
    def test_ingest_company_inactive_adapter(self, mock_get_adapter):
        # Arrange
        company = {"ats_provider": "inactive_provider"}
        mock_adapter = MagicMock()
        mock_adapter.active = False
        mock_get_adapter.return_value = mock_adapter

        # Act
        result = ingest_company(company)

        # Assert
        self.assertEqual(result["error"], "inactive_ats_adapter")
        self.assertEqual(result["fetched"], 0)

    @patch("app.workers.ingestion.employer.get_adapter")
    @patch("app.workers.ingestion.employer.fetch_company_jobs", return_value=(None, "fetch_failed"))
    @patch("app.workers.ingestion.employer.get_engine")
    @patch("app.workers.ingestion.employer.mark_ats_synced")
    def test_ingest_company_fetch_error(self, mock_mark_synced, mock_get_engine, mock_fetch, mock_get_adapter):
        # Arrange
        company = {"ats_provider": "test_provider", "company_ats_id": "ats1"}
        mock_get_adapter.return_value = MagicMock()
        
        mock_conn = MagicMock()
        mock_get_engine.return_value.begin.return_value.__enter__.return_value = mock_conn

        # Act
        result = ingest_company(company)

        # Assert
        mock_mark_synced.assert_called_once_with(mock_conn, "ats1", success=False)
        self.assertEqual(result["error"], "fetch_failed")
        self.assertEqual(result["fetched"], 0)

    @patch("app.workers.ingestion.employer.get_adapter")
    @patch("app.workers.ingestion.employer.fetch_company_jobs")
    @patch("app.workers.ingestion.employer.get_engine")
    def test_ingest_company_transaction_fails(self, mock_get_engine, mock_fetch, mock_get_adapter):
        # Arrange
        company = {"ats_provider": "test_provider"}
        mock_get_adapter.return_value = MagicMock()
        raw_jobs = [{"id": "job1"}]
        mock_fetch.return_value = (raw_jobs, None)

        mock_engine = MagicMock()
        mock_engine.begin.side_effect = Exception("DB transaction failed")
        mock_get_engine.return_value = mock_engine

        # Act
        result = ingest_company(company)

        # Assert
        self.assertEqual(result["error"], "transaction_failed")
        self.assertEqual(result["fetched"], 1)
        self.assertEqual(result["normalized_count"], 0)
        self.assertEqual(result["accepted"], 0)