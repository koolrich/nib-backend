locals {
  common_tags = {
    Project = var.project
    Environment = var.environment
  }
}

resource "aws_lambda_function" "this" {
  function_name = var.lambda_function_name
  role          = var.lambda_role_arn
  handler       = var.lambda_handler
  runtime       = "python3.13"
  source_code_hash = var.source_code_hash

  s3_bucket = var.lambda_artifact_bucket
  s3_key    = var.lambda_s3_key

  layers = [var.lambda_layer_arn]

  environment {
    variables = var.lambda_environment_variables
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = [var.lambda_sg_id]
  }
}
