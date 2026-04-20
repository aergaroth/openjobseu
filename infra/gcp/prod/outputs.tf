output "service_url" {
  value = google_cloud_run_v2_service.this.uri
}

output "audit_bastion_instance_name" {
  value = google_compute_instance.audit_bastion.name
}

output "audit_bastion_zone" {
  value = google_compute_instance.audit_bastion.zone
}

output "audit_bastion_local_port" {
  value = local.audit_bastion_port
}
