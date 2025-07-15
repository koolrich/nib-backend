provider "aws" {
  region = var.aws_region
}

locals {
  common_tags = {
    Project = var.project
    
  }
}

terraform {
  backend "s3" {
    bucket         = "nib-terraform-state-1"
    key            = "envs/dev/terraform.tfstate"
    region         = "eu-west-2"
    use_lockfile   = true
    encrypt        = true
  }
}

module "vpc" {
  source      = "../../modules/vpc"
  project     = var.project
  cidr_block  = var.vpc_cidr
  aws_region  = var.aws_region
  name        = "nib-vpc"
  subnets     = var.subnets
  lambda_sg_name = "nib-lambda-sg"
  environment = var.environment
}

module "db" {
  source                = "../../modules/db"
  db_user               = var.db_user
  db_name               = var.db_name
  db_sg_name = "nib-db-sg"
  subnet_ids            = module.vpc.db_subnet_ids
  vpc_id                = module.vpc.vpc_id
  lambda_sg_id          = module.vpc.lambda_sg_id
  db_subnet_group_name  = "nib-db-subnet-group"
  project               = var.project
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

resource "aws_iam_role" "nib_lambda_execution_role" {
  name = "NIBLambdaExecutionRole-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })

 tags = local.common_tags
}

data "aws_caller_identity" "current" {}

resource "aws_iam_policy" "nib_lambda_policy" {
  name = "NIBLambdaPolicy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "CloudWatchLogging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "SSMParameterAccess"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/nib/*"
      },
      {
        Sid    = "AllowSMSPublish"
        Effect = "Allow"
        Action = "sns:Publish"
        Resource = "*"
        # This wildcard is required when publishing SMS messages directly to phone numbers
      },
      {
        Sid = "LambdaFunctionCreationAccess"
        Effect = "Allow",
        Action = [
          "lambda:CreateFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration"
        ],
        Resource = "*"
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.nib_lambda_execution_role.name
  policy_arn = aws_iam_policy.nib_lambda_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.nib_lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}


resource "aws_lambda_layer_version" "shared_layer" {
  s3_bucket           = var.lambda_artifact_bucket
  s3_key              = "layers/layer.zip"
  layer_name          = "shared_layer"
  compatible_runtimes = ["python3.13"]
}

module "lambda_function_send_invite" {
  source = "../../modules/lambda"
  lambda_artifact_bucket      = var.lambda_artifact_bucket
  lambda_s3_key               = "functions/send_invite.zip"
  lambda_function_name        = "send_invite"
  lambda_role_arn             = aws_iam_role.nib_lambda_execution_role.arn
  lambda_handler              = "send_invite.lambda_handler"
  lambda_layer_arn            = aws_lambda_layer_version.shared_layer.arn
  lambda_environment_variables = {
    ENV = "dev"
  }
  vpc_subnet_ids              = module.vpc.lambda_subnet_ids
  vpc_id = module.vpc.vpc_id
  lambda_sg_id = module.vpc.lambda_sg_id
  project = var.project
  environment = var.environment
}

