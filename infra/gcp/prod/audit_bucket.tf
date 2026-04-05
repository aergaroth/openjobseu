# Private bucket for internal audit snapshots — not publicly accessible.

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

output "audit_bucket_name" {
  value       = google_storage_bucket.audit_internal.name
  description = "Private bucket name for audit snapshots"
}
