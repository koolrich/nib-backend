output "db_host" {
  value = aws_db_instance.nib_db.address
}

output "db_port" {
  value = aws_db_instance.nib_db.port
}

output "db_name" {
  value = aws_db_instance.nib_db.db_name
}

output "nib_db_sg_id" {
  value = aws_security_group.nib_db_sg.id
}
