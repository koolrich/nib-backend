output "user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = aws_cognito_user_pool.nib_user_pool.id
}

output "app_client_id" {
  description = "ID of the Cognito app client"
  value       = aws_cognito_user_pool_client.nib_app_client.id
}