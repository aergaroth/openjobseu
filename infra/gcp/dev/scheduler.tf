resource "google_service_account" "scheduler_sa" {
  account_id   = "scheduler-internal"
  display_name = "Cloud Scheduler Internal Caller"
}

resource "google_cloud_tasks_queue" "tick_pipeline" {
  name     = "openjobseu-tick-pipeline"
  location = var.queue_region

  rate_limits {
    max_concurrent_dispatches = 1
    max_dispatches_per_second = 1
  }

  retry_config {
    max_attempts       = 5
    min_backoff        = "30s"
    max_backoff        = "600s"
    max_doublings      = 5
    max_retry_duration = "0s"
  }
}

resource "google_cloud_scheduler_job" "tick_ingestion" {
  name      = "openjobseu-tick-ingestion"
  region    = var.scheduler_region
  schedule  = "0 * * * *" # co godzinę (np. 12:00, 13:00)
  time_zone = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tick?group=ingestion"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

resource "google_cloud_scheduler_job" "dorking_discovery" {
  name      = "openjobseu-dorking"
  region    = var.scheduler_region
  schedule  = "0 2 * * *" # o 02:00 w nocy każdego dnia
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tasks/dorking"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

resource "google_cloud_scheduler_job" "tick_maintenance" {
  name      = "openjobseu-tick-maintenance"
  region    = var.scheduler_region
  schedule  = "0 4 * * *" # o 04:00 rano każdego dnia
  time_zone = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tick?group=maintenance"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

resource "google_cloud_scheduler_job" "discovery" {
  name      = "openjobseu-discovery"
  region    = var.scheduler_region
  schedule  = "0 6 * * *" # o 06:00 rano każdego dnia
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/discovery/run"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}