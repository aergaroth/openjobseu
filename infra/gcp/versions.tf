terraform {
  required_version = ">= 1.5"

  backend "gcs" {
    bucket  = "openjobseu-tfstate"
    prefix  = "cloud-run"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
