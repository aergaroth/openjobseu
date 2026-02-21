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

#variable "scheduler_region" {
#  type        = string
#  description = "Region for Cloud Scheduler"
#  default     = "europe-west1"
#}
