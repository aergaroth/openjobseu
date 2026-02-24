terraform {

  backend "gcs" {
    bucket = "openjobseu-tfstate"
    prefix = "prod/cloud-run"
  }

}

