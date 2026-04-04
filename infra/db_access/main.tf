provider "aws" {
  region = var.aws_region
}

terraform {
  backend "s3" {
    bucket       = "nib-terraform-state-1"
    key          = "envs/db-access/terraform.tfstate"
    region       = "eu-west-2"
    use_lockfile = true
    encrypt      = true
  }
}

data "aws_caller_identity" "current" {}

# ── Look up shared infra by tags ───────────────────────────────────────────────

data "aws_vpc" "nib" {
  filter {
    name   = "tag:Project"
    values = ["nib"]
  }
  filter {
    name   = "tag:Environment"
    values = [var.env]
  }
}

data "aws_subnet" "private" {
  filter {
    name   = "tag:Role"
    values = ["lambda"]
  }
  filter {
    name   = "tag:Environment"
    values = [var.env]
  }
}

data "aws_route_table" "private" {
  subnet_id = data.aws_subnet.private.id
}
