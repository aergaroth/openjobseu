data "google_project" "current" {}

locals {
  # Wymuszenie deterministycznego URL dla Cloud Run (omija problemy z weryfikacją OIDC na starych adresach)
  run_uri = "https://${var.service_name}-${data.google_project.current.number}.${var.region}.run.app"
}

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
  name             = "openjobseu-tick-ingestion"
  region           = var.scheduler_region
  schedule         = "*/35 * * * *" # every 35 minutes
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tick?group=ingestion"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "ping_ingestion" {
  name             = "openjobseu-ping-ingestion"
  region           = var.scheduler_region
  schedule         = "*/30 * * * *" # every 30 minutes
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "GET"
    uri         = "${local.run_uri}/health"

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "ping_dorking" {
  name             = "openjobseu-ping-dorking"
  region           = var.scheduler_region
  schedule         = "15 3 * * *" # at 03:15 AM — warms up the instance 5 min before dorking
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "GET"
    uri         = "${local.run_uri}/health"

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "dorking_discovery" {
  name             = "openjobseu-dorking"
  region           = var.scheduler_region
  schedule         = "20 3 * * *" # at 03:20 AM every day (off-peak, staggered)
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tasks/dorking"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "tick_maintenance" {
  name             = "openjobseu-tick-maintenance"
  region           = var.scheduler_region
  schedule         = "5 */4 * * *" # at minute 5 past every 4th hour (staggered)
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tick?group=maintenance"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "discovery_company_sources" {
  name             = "openjobseu-discovery-company-sources"
  region           = var.scheduler_region
  schedule         = "10 */6 * * *" # at minute 10 past every 6th hour
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tasks/company-sources"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "discovery_careers" {
  name             = "openjobseu-discovery-careers"
  region           = var.scheduler_region
  schedule         = "30 */6 * * *" # at minute 30 past every 6th hour
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tasks/careers"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "discovery_ats_reverse" {
  name             = "openjobseu-discovery-ats-reverse"
  region           = var.scheduler_region
  schedule         = "50 */6 * * *" # at minute 50 past every 6th hour
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tasks/ats-reverse"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "discovery_guess" {
  name             = "openjobseu-discovery-guess"
  region           = var.scheduler_region
  schedule         = "10 1-23/6 * * *" # at minute 10 one hour after each discovery batch starts
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "${local.run_uri}/internal/tasks/guess"

    headers = {
      Content-Type = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}

resource "google_cloud_scheduler_job" "ping_discovery" {
  name             = "openjobseu-ping-discovery"
  region           = var.scheduler_region
  schedule         = "5 */6 * * *" # at minute 5 past every 6th hour
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "GET"
    uri         = "${local.run_uri}/health"

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
      audience              = local.run_uri
    }
  }
}
