variable "project" {
  type        = string
  description = "Project name for tagging"
}

variable "environment" {
  type        = string
  description = "Environment"
}

variable "user_pool_name" {
  type        = string
  description = "Name of the Cognito user pool"
}

variable "app_client_name" {
  type        = string
  description = "Name of the Cognito app client"
}

variable "explicit_auth_flows" {
  type        = list(string)
  description = "List of allowed auth flows"
}

variable "generate_secret" {
  type        = bool
  description = "Whether to generate a secret for the app client"
  default     = false
}

variable "password_min_length" {
  type        = number
  default     = 8
  description = "Minimum password length"
}

variable "password_require_numbers" {
  type        = bool
  default     = true
  description = "Require numbers in password"
}

variable "password_require_lowercase" {
  type        = bool
  default     = true
  description = "Require lowercase letters in password"
}