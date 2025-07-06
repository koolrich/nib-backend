output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.nib_vpc.id
}

output "subnet_ids" {
  description = "List of subnet IDs"
  value       = [for s in aws_subnet.nib_subnets : s.id]
}

output "lambda_sg_id" {
  description = "Lambda SG ID"
  value       = aws_security_group.nib_lambda_sg.id
}