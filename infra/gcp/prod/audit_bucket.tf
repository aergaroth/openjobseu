# Private bucket for internal audit snapshots — not publicly accessible.
# Consumed by Appsmith via the appsmith-reader service account.

resource "google_storage_bucket" "audit_internal" {
  name                        = "${var.project_id}-audit-internal"
  location                    = "EU"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

# Cloud Run runtime can write audit_snapshot.json
resource "google_storage_bucket_iam_member" "cloud_run_audit_write" {
  bucket = google_storage_bucket.audit_internal.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:cloudrun-prod-runtime@${var.project_id}.iam.gserviceaccount.com"

  condition {
    title      = "audit_snapshot_only"
    expression = "resource.name == \"projects/_/buckets/${google_storage_bucket.audit_internal.name}/objects/audit_snapshot.json\""
  }
}

# Service account for Appsmith (read-only)
resource "google_service_account" "appsmith_reader" {
  account_id   = "appsmith-reader"
  display_name = "Appsmith Read-Only Audit Access"
}

resource "google_storage_bucket_iam_member" "appsmith_reader_audit" {
  bucket = google_storage_bucket.audit_internal.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.appsmith_reader.email}"
}

# Cloud Run SA może podpisywać URL-e przez IAM SignBlob API
# (potrzebne do blob.generate_signed_url() bez klucza prywatnego w pamięci)
resource "google_service_account_iam_member" "cloud_run_self_sign" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/cloudrun-prod-runtime@${var.project_id}.iam.gserviceaccount.com"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:cloudrun-prod-runtime@${var.project_id}.iam.gserviceaccount.com"
}

output "audit_bucket_name" {
  value       = google_storage_bucket.audit_internal.name
  description = "Private bucket name for audit snapshots"
}

output "appsmith_reader_email" {
  value       = google_service_account.appsmith_reader.email
  description = "Service account email to use in Appsmith GCS connector"
}
