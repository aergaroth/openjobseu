terraform {

  backend "gcs" {
    bucket  = "dev-openjobseu-tfstate"
    prefix  = "dev/cloud-run"
  }

}

