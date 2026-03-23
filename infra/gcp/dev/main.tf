provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "google-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_api_key" {
  secret      = google_secret_manager_secret.google_api_key.id
  secret_data = var.google_api_key
}

resource "google_secret_manager_secret_iam_member" "cloud_run_google_api_key" {
  secret_id = google_secret_manager_secret.google_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:cloudrun-dev-runtime@dev-openjobseu.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret" "google_cse_id" {
  secret_id = "google-cse-id"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_cse_id" {
  secret      = google_secret_manager_secret.google_cse_id.id
  secret_data = var.google_cse_id
}

resource "google_secret_manager_secret_iam_member" "cloud_run_google_cse_id" {
  secret_id = google_secret_manager_secret.google_cse_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:cloudrun-dev-runtime@dev-openjobseu.iam.gserviceaccount.com"
}


resource "google_cloud_run_v2_service" "this" {
  name     = var.service_name
  location = var.region
  deletion_protection = false

  lifecycle {
    ignore_changes = [template[0].scaling]
  }

  template {

    service_account = "cloudrun-dev-runtime@dev-openjobseu.iam.gserviceaccount.com"

    timeout = "180s"

    containers {
      image = var.image

      resources {
        cpu_idle = true
        limits = {
          memory = "1024Mi"
          cpu    = "1000m"
        }
      }

      env {
        name  = "INGESTION_MODE"
        value = "dev"
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
        name  = "SCHEDULER_SA_EMAIL"
        value = google_service_account.scheduler_sa.email
      }
      env {
        name  = "TICK_TASK_QUEUE_PROJECT"
        value = var.project_id
      }
      env {
        name  = "TICK_TASK_QUEUE_LOCATION"
        value = var.queue_region
      }
      env {
        name  = "TICK_TASK_QUEUE_NAME"
        value = google_cloud_tasks_queue.tick_pipeline.name
      }
      env {
        name  = "BASE_URL"
        value = local.run_uri
      }
      env {
        name  = "TICK_TASK_DISPATCH_DEADLINE"
        value = "180s"
      }
      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_CSE_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_cse_id.secret_id
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

resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.this.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

resource "google_project_iam_member" "cloud_run_tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:cloudrun-dev-runtime@dev-openjobseu.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "cloud_run_can_act_as_scheduler" {
  service_account_id = google_service_account.scheduler_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:cloudrun-dev-runtime@dev-openjobseu.iam.gserviceaccount.com"
}
