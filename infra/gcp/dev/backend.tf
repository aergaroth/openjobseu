terraform {

  backend "gcs" {
    bucket  = "openjobseu-tfstate-dev"
    prefix  = "dev/cloud-run"
  }

}

