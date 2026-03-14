variable "project_id" {
  type        = string
  description = "GCP project id"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "europe-north1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name"
  default     = "dev-openjobseu"
}

variable "image" {
  type        = string
  description = "Container image URL"
}


variable "google_client_id" {
  type        = string
  description = "Google OAuth Client ID"
  default     = "dummy-client-id"
}

variable "google_client_secret" {
  type        = string
  description = "Google OAuth Client Secret"
  sensitive   = true
  default     = "dummy-client-secret"
}

variable "session_secret_key" {
  type        = string
  description = "Secret key for signing session cookies"
  sensitive   = true
}

variable "allowed_auth_email" {
  type        = string
  description = "Email allowed to access the audit panel"
}
