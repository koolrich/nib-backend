output "security_group_id" {
  description = "ID of the security group created for this VPC interface endpoint"
  value       = aws_security_group.vpc_interface_endpoints_sg.id
}
