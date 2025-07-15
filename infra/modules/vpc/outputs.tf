output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.nib_vpc.id
}

output "subnet_ids" {
  description = "List of subnet IDs"
  value       = [for s in aws_subnet.nib_subnets : s.id]
}

output "db_subnet_ids" {
  value = [for s in aws_subnet.nib_subnets : s.id if s.tags["Role"] == "db"]
}

output "lambda_subnet_ids" {
  value = [for s in aws_subnet.nib_subnets : s.id if s.tags["Role"] == "lambda"]
}

output "lambda_sg_id" {
  description = "Lambda SG ID"
  value       = aws_security_group.nib_lambda_sg.id
}