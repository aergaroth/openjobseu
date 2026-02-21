provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_cloud_run_v2_service" "this" {
  name     = var.service_name
  location = var.region

  template {
    containers {
      image = var.image

      env {
        name  = "INGESTION_MODE"
        value = "prod"
      }
      ports {
        container_port = 8000
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.this.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
