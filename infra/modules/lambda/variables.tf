variable "lambda_function_name" {
  description = "Lambda function name"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM Role ARN for Lambda"
  type        = string
}

variable "lambda_handler" {
  description = "Lambda function handler"
  type        = string
}

variable "lambda_artifact_bucket" {
  description = "S3 bucket for Lambda artifact"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key for Lambda artifact"
  type        = string
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda Layer"
  type        = string
}

variable "lambda_environment_variables" {
  description = "Environment variables for Lambda function"
  type        = map(string)
}

variable "vpc_subnet_ids" {
  description = "List of VPC subnet IDs for Lambda"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of Security Group IDs for Lambda"
  type        = list(string)
}