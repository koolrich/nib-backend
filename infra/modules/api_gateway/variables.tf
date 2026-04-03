variable "project" {
  type        = string
  description = "Project name for tagging"
}

variable "environment" {
  type        = string
  description = "Environment"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
}

variable "api_name" {
  type        = string
  description = "Name of the HTTP API"
}

variable "cognito_user_pool_id" {
  type        = string
  description = "Cognito user pool ID — used to build the JWT authorizer issuer URL"
}

variable "cognito_app_client_id" {
  type        = string
  description = "Cognito app client ID — used as the JWT authorizer audience"
}

variable "routes" {
  description = "Map of routes to Lambda config. Key format: 'METHOD /path' (e.g. 'POST /auth/login')"
  type = map(object({
    lambda_invoke_arn = string
    lambda_arn        = string
    requires_auth     = bool
  }))
}
