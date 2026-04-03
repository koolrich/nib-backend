output "api_endpoint" {
  description = "Base URL of the HTTP API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "api_id" {
  description = "ID of the HTTP API"
  value       = aws_apigatewayv2_api.this.id
}
