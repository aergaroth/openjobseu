resource "google_logging_metric" "tick_finished" {
  name   = "tick_finished_count"
  filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.phase=\"tick_finished\""
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

resource "google_monitoring_notification_channel" "email_alerts" {
  display_name = "Pipeline alerts (email)"
  type         = "email"
  labels = {
    email_address = var.allowed_auth_email
  }
}

resource "google_monitoring_alert_policy" "tick_failure" {
  display_name = "[DEV] Pipeline tick — failed steps"
  combiner     = "OR"

  conditions {
    display_name = "tick_finished with sources_failed > 0"
    condition_matched_log {
      filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.phase=\"tick_finished\" AND jsonPayload.sources_failed>0"
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_alerts.name]

  alert_strategy {
    notification_rate_limit {
      period = "600s"
    }
    auto_close = "86400s"
  }

  documentation {
    content = "A pipeline tick completed with at least one failed step. Check Cloud Run logs (filter: jsonPayload.phase=\"tick_finished\")."
  }
}

resource "google_monitoring_alert_policy" "tick_absent" {
  display_name = "[DEV] Pipeline tick — not running"
  combiner     = "OR"

  conditions {
    display_name = "No tick_finished log in last 2 hours"
    condition_absent {
      filter   = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.tick_finished.name}\" AND resource.type=\"cloud_run_revision\""
      duration = "7200s"
      aggregations {
        alignment_period     = "600s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_alerts.name]

  alert_strategy {
    auto_close = "86400s"
  }

  documentation {
    content = "No pipeline tick has completed in the last 2 hours. Cloud Scheduler or Cloud Run may be down."
  }
}
