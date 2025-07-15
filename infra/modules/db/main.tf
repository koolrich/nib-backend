locals {
  common_tags = {
    Project = var.project,
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "nib_db_subnet_group" {
  name       = var.db_subnet_group_name
  subnet_ids = var.subnet_ids

  tags = merge(local.common_tags, {
    Name = var.db_subnet_group_name
  })
}

resource "aws_security_group" "nib_db_sg" {
  name   = var.db_sg_name
  vpc_id = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.lambda_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = var.db_sg_name
  })
}
resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "aws_ssm_parameter" "db_username" {
  name        = "/nib/db/username"
  type        = "String"
  value       = var.db_user
  description = "RDS DB User"

  tags = local.common_tags
}

resource "aws_ssm_parameter" "db_password" {
  name        = "/nib/db/password"
  type        = "SecureString"
  value       = random_password.db_password.result
  description = "RDS DB Password"

 tags = local.common_tags
}

resource "aws_db_instance" "nib_db" {
  identifier             = "nib-db"
  engine                 = "postgres"
  engine_version         = "15.13"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = "nibdb"
  username               = aws_ssm_parameter.db_username.value
  password               = aws_ssm_parameter.db_password.value
  db_subnet_group_name   = aws_db_subnet_group.nib_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.nib_db_sg.id]
  multi_az               = false
  publicly_accessible    = false
  skip_final_snapshot    = true

  tags = merge(local.common_tags, {
    Name = "nib-db"
  })
}

resource "aws_ssm_parameter" "db_host" {
  name        = "/nib/db/host"
  type        = "String"
  value       = aws_db_instance.nib_db.address
  description = "RDS DB Host"
  tags = local.common_tags
}

resource "aws_ssm_parameter" "db_port" {
  name        = "/nib/db/port"
  type        = "String"
  value       = aws_db_instance.nib_db.port
  description = "RDS DB Port"
  tags = local.common_tags
}

resource "aws_ssm_parameter" "db_name" {
  name        = "/nib/db/name"
  type        = "String"
  value       = aws_db_instance.nib_db.db_name
  description = "RDS DB Name"
  tags = local.common_tags
}