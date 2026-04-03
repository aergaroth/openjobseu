variable "project_id" {
  type        = string
  description = "GCP project id"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "europe-north1"
}

variable "queue_region" {
  type        = string
  description = "Region for Cloud Tasks queue"
  default     = "europe-west1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name"
  default     = "openjobseu"
}

variable "image" {
  type        = string
  description = "Container image URL"
}

variable "scheduler_region" {
  type        = string
  description = "Region for Cloud Scheduler"
  default     = "europe-west1"
}

variable "google_client_id" {
  type        = string
  description = "Google OAuth Client ID"
  sensitive   = true
}

variable "google_client_secret" {
  type        = string
  description = "Google OAuth Client Secret"
  sensitive   = true
}

variable "session_secret_key" {
  type        = string
  description = "Secret key for securing browser sessions"
  sensitive   = true
}

variable "allowed_auth_email" {
  type        = string
  description = "Email address authorized to access the admin panel"
}

variable "google_api_key" {
  type        = string
  description = "Google Custom Search API Key"
  sensitive   = true
}

variable "google_cse_id" {
  type        = string
  description = "Google Custom Search Engine ID"
  sensitive   = true
}

variable "slack_webhook_url" {
  type        = string
  description = "Slack incoming webhook URL for pipeline failure alerts"
  sensitive   = true
  default     = ""
}

variable "artifact_registry_repository_id" {
  type        = string
  description = "Artifact Registry repository used by GitHub Actions in prod"
  default     = "openjobseu"
}

variable "terraform_state_bucket" {
  type        = string
  description = "GCS bucket storing the Terraform remote state for prod"
  default     = "openjobseu-tfstate"
}

variable "public_feed_bucket" {
  type        = string
  description = "Public bucket receiving deploy-time frontend assets"
  default     = "openjobseu.org"
}

variable "github_repository_owner" {
  type        = string
  description = "GitHub organization/user allowed to federate into prod GCP"
  default     = "aergaroth"
}

variable "github_repository_name" {
  type        = string
  description = "GitHub repository allowed to federate into prod GCP"
  default     = "openjobseu"
}
