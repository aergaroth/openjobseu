provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_cloud_run_v2_service" "this" {
  name     = var.service_name
  location = var.region
  deletion_protection = false
  service_account = "cloudrun-dev-runtime@dev-openjobseu.iam.gserviceaccount.com"

  lifecycle {
   ignore_changes = [
     scaling
   ]
  }


  template {
    timeout = "180s"
    containers {
      image = var.image
      resources {
        cpu_idle = true
      }


     env {
        name  = "INGESTION_MODE"
        value = "dev"
     }


     env {
        name = "DB_MODE"
        value = "standard"
     }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "openjobseu-db-url"
            version = "latest"
          }
        }
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
