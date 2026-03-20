resource "google_cloud_tasks_queue" "tick_pipeline" {
  name     = "openjobseu-tick-pipeline"
  location = var.scheduler_region

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
  schedule  = "*/15 * * * *" # every 15 minutes
  time_zone = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tick?group=ingestion"

    headers = {
      Content-Type      = "application/json"
      X-Internal-Secret = random_password.internal_secret.result
    }
  }
}

resource "google_cloud_scheduler_job" "dorking_discovery" {
  name      = "openjobseu-dorking"
  region    = var.scheduler_region
  schedule  = "0 3 * * *" # at 03:00 AM every day (off-peak)
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tasks/dorking"

    headers = {
      Content-Type      = "application/json"
      X-Internal-Secret = random_password.internal_secret.result
    }
  }
}

resource "google_cloud_scheduler_job" "tick_maintenance" {
  name      = "openjobseu-tick-maintenance"
  region    = var.scheduler_region
  schedule  = "0 * * * *" # at minute 0 past every hour
  time_zone = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tick?group=maintenance"

    headers = {
      Content-Type      = "application/json"
      X-Internal-Secret = random_password.internal_secret.result
    }
  }
}

resource "google_cloud_scheduler_job" "discovery" {
  name      = "openjobseu-discovery"
  region    = var.scheduler_region
  schedule  = "0 */6 * * *" # at minute 0 past every 6th hour
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/discovery/run"

    headers = {
      Content-Type      = "application/json"
      X-Internal-Secret = random_password.internal_secret.result
    }
  }
}
