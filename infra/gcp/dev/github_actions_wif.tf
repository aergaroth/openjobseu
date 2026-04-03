locals {
  github_repository_full_name = "${var.github_repository_owner}/${var.github_repository_name}"
  github_ref_subject         = "repo:${var.github_repository_owner}/${var.github_repository_name}:ref:refs/heads/develop"
  github_pr_subject          = "repo:${var.github_repository_owner}/${var.github_repository_name}:pull_request"
}

data "google_service_account" "cloud_run_runtime" {
  account_id = "cloudrun-dev-runtime"
}

resource "google_iam_workload_identity_pool" "github_actions" {
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
  description               = "OIDC trust for GitHub Actions workflows in ${local.github_repository_full_name}."
}

resource "google_iam_workload_identity_pool_provider" "github_actions" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-openjobseu"
  display_name                       = "GitHub openjobseu"
  description                        = "Accept GitHub Actions OIDC tokens for deploy and Terraform plan in ${local.github_repository_full_name}."

  attribute_condition = join(" && ", [
    "assertion.repository == '${local.github_repository_full_name}'",
    "assertion.repository_owner == '${var.github_repository_owner}'",
    "((assertion.event_name in ['push', 'workflow_dispatch']) && assertion.ref == 'refs/heads/develop') || (assertion.event_name == 'pull_request' && assertion.base_ref == 'develop')",
  ])

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
    "attribute.base_ref"   = "assertion.base_ref"
    "attribute.event_name" = "assertion.event_name"
    "attribute.actor"      = "assertion.actor"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "github_deploy" {
  account_id   = "github-deploy"
  display_name = "GitHub Actions deploy"
  description  = "Builds the container image and applies Terraform for the dev environment."
}

resource "google_service_account" "github_terraform_plan" {
  account_id   = "github-terraform-plan"
  display_name = "GitHub Actions terraform plan"
  description  = "Reads Terraform state and infrastructure metadata for dev pull request plans."
}

resource "google_service_account_iam_member" "github_deploy_wif_user" {
  service_account_id = google_service_account.github_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions.name}/subject/${local.github_ref_subject}"
}

resource "google_service_account_iam_member" "github_plan_wif_user" {
  service_account_id = google_service_account.github_terraform_plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions.name}/subject/${local.github_pr_subject}"
}

resource "google_artifact_registry_repository_iam_member" "github_deploy_repo_writer" {
  location   = var.region
  repository = var.artifact_registry_repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_storage_bucket_iam_member" "github_deploy_tfstate_admin" {
  bucket = var.terraform_state_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_storage_bucket_iam_member" "github_plan_tfstate_viewer" {
  bucket = var.terraform_state_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.github_terraform_plan.email}"
}

resource "google_project_iam_member" "github_deploy_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_cloud_scheduler_admin" {
  project = var.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_cloud_tasks_admin" {
  project = var.project_id
  role    = "roles/cloudtasks.admin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_secret_manager_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_workload_identity_pool_admin" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolAdmin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_service_account_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_project_iam_admin" {
  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_monitoring_editor" {
  project = var.project_id
  role    = "roles/monitoring.editor"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_logging_config_writer" {
  project = var.project_id
  role    = "roles/logging.configWriter"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_service_account_iam_member" "github_deploy_runtime_user" {
  service_account_id = data.google_service_account.cloud_run_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_service_account_iam_member" "github_deploy_scheduler_user" {
  service_account_id = google_service_account.scheduler_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_plan_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.github_terraform_plan.email}"
}

resource "google_project_iam_member" "github_plan_service_account_viewer" {
  project = var.project_id
  role    = "roles/iam.serviceAccountViewer"
  member  = "serviceAccount:${google_service_account.github_terraform_plan.email}"
}

resource "google_project_iam_member" "github_plan_workload_identity_pool_viewer" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolViewer"
  member  = "serviceAccount:${google_service_account.github_terraform_plan.email}"
}

resource "google_project_iam_member" "github_plan_secret_manager_viewer" {
  project = var.project_id
  role    = "roles/secretmanager.viewer"
  member  = "serviceAccount:${google_service_account.github_terraform_plan.email}"
}

output "github_actions_workload_identity_provider" {
  description = "Full Workload Identity Provider resource name for GitHub Actions in dev."
  value       = google_iam_workload_identity_pool_provider.github_actions.name
}

output "github_actions_deploy_service_account" {
  description = "Service account email for dev build + deploy workflow impersonation."
  value       = google_service_account.github_deploy.email
}

output "github_actions_terraform_plan_service_account" {
  description = "Service account email for dev Terraform plan workflow impersonation."
  value       = google_service_account.github_terraform_plan.email
}
