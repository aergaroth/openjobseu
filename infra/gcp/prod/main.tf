provider "google" {
  project = var.project_id
  region  = var.region
}

resource "random_password" "internal_secret" {
  length  = 32
  special = false
}

resource "google_cloud_run_v2_service" "this" {
  name     = var.service_name
  location = var.region
  deletion_protection = true

  template {

    service_account = "cloudrun-prod-runtime@openjobseu.iam.gserviceaccount.com"

    timeout = "180s"

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "INGESTION_MODE"
        value = "prod"
      }

      env {
        name  = "DB_MODE"
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

      env {
        name  = "GOOGLE_CLIENT_ID"
        value = var.google_client_id
      }
      env {
        name  = "GOOGLE_CLIENT_SECRET"
        value = var.google_client_secret
      }
      env {
        name  = "SESSION_SECRET_KEY"
        value = var.session_secret_key
      }
      env {
        name  = "ALLOWED_AUTH_EMAIL"
        value = var.allowed_auth_email
      }
      env {
        name  = "INTERNAL_SECRET"
        value = random_password.internal_secret.result
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
