locals {
  common_tags = {
    Project = var.project
    Environment = var.environment
  }
}

resource "aws_cognito_user_pool" "nib_user_pool" {
  name = var.user_pool_name

  password_policy {
    minimum_length    = var.password_min_length
    require_numbers   = var.password_require_numbers
    require_lowercase = var.password_require_lowercase
  }

  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "nib_app_client" {
  name         = var.app_client_name
  user_pool_id = aws_cognito_user_pool.nib_user_pool.id

  explicit_auth_flows = var.explicit_auth_flows
  generate_secret      = var.generate_secret
}