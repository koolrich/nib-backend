provider "aws" {
  region = var.aws_region

  assume_role {
    role_arn     = var.role_arn
    session_name = var.role_session_name
  }
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
  filter {
    name   = "tag:Environment"
    values = [var.env]
  }
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.nib.id]
  }
}
