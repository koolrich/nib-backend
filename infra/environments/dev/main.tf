provider "aws" {
  region = var.aws_region

  assume_role {
    role_arn     = "arn:aws:iam::021891595998:role/TerraformUserRole"
    session_name = "terraform-session"
  }
}

terraform {
  backend "s3" {
    bucket         = "nib-terraform-state-1"
    key            = "envs/dev/terraform.tfstate"
    region         = "eu-west-2"
    use_lockfile   = true
    encrypt        = true
    assume_role = {
        role_arn = "arn:aws:iam::021891595998:role/TerraformUserRole"
        role_session_name = "terraform-state-access"
       
    }
  }
}

module "vpc" {
  source      = "../../modules/vpc"
  project     = var.project
  cidr_block  = var.vpc_cidr
  aws_region  = var.aws_region
  name        = "nib-vpc"
  subnets     = var.subnets
  environment = var.environment
}

module "db" {
  source                = "../../modules/db"
  db_user               = var.db_user
  db_name               = var.db_name
  subnet_ids            = module.vpc.subnet_ids
  vpc_id                = module.vpc.vpc_id
  lambda_sg_id          = module.vpc.lambda_sg_id
  project               = var.project
  db_subnet_group_name  = "nib-db-subnet-group"
  environment = var.environment
}

module "cognito" {
  source            = "../../modules/cognito"
  project           = var.project
  user_pool_name    = "nib-user-pool"
  app_client_name   = "nib-app-client"
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
  generate_secret           = false
  password_min_length       = 8
  password_require_numbers  = true
  password_require_lowercase = true
  environment = var.environment
}

