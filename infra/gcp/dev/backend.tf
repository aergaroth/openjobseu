terraform {

  backend "gcs" {
    bucket  = "openjobseu-tfstate"
    prefix  = "dev/cloud-run"
  }

}

