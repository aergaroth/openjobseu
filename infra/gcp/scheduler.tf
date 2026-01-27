resource "google_cloud_scheduler_job" "tick" {
  name     = "openjobseu-tick"
  region   = var.scheduler_region
  schedule = "*/5 * * * *" # every 5 minutes
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.this.uri}/internal/tick"

    headers = {
      Content-Type = "application/json"
    }
  }
}
