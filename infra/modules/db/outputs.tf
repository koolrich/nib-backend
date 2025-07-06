output "db_host" {
  value = aws_db_instance.nib_rds.address
}

output "db_port" {
  value = aws_db_instance.nib_rds.port
}

output "db_name" {
  value = aws_db_instance.nib_rds.db_name
}

output "rds_sg_id" {
  value = aws_security_group.nib_rds_sg.id
}
