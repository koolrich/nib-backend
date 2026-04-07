variable "aws_region" {
    default = "eu-west-2"
}
variable "role_arn" {
    default = "arn:aws:iam::021891595998:role/TerraformUserRole"
}
variable "role_session_name" {
    default = "terraform-session"
}
variable "project" {
    default = "nib"
}
variable "environment" {
    default = "prod"
}
variable "vpc_cidr" {
    default = "10.1.0.0/16"
}
variable "subnets" {
  default = {
    "nib-subnet-1" = {
      cidr = "10.1.1.0/24"
      az   = "a"
      role = "db"
    }
    "nib-subnet-2" = {
      cidr = "10.1.2.0/24"
      az   = "b"
      role = "db"
    }
    "nib-subnet-3" = {
      cidr = "10.1.3.0/24"
      az   = "c"
      role = "lambda"
    }
  }
}
variable "db_user" {
    default = "nibadmin"
}
variable "db_name" {
    default = "nibdb"
}

variable "lambda_artifact_bucket" {
    type    = string
    default = "nib-lambda-artifacts"
}

variable "twilio_account_sid" {
  type      = string
  sensitive = true
}

variable "twilio_auth_token" {
  type      = string
  sensitive = true
}

variable "twilio_from_number" {
  type    = string
  default = "NIB"
}
