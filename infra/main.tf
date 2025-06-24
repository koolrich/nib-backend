provider "aws" {
  region = var.aws_region

  assume_role {
    role_arn     = var.role_arn
    session_name = var.role_session_name
  }
}

resource "aws_vpc" "nib_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Project = "nib"
    Name    = "nib-vpc"
  }
}

resource "aws_subnet" "nib_subnets" {
  for_each = var.subnets

  vpc_id            = aws_vpc.nib_vpc.id
  cidr_block        = each.value.cidr
  availability_zone = "${var.aws_region}${each.value.az}"

  tags = {
    Project = "nib"
    Name    = each.key
  }
}

resource "aws_db_subnet_group" "nib_db_subnet_group" {
  name       = "main"
  subnet_ids = [for subnet in aws_subnet.nib_subnets : subnet.id]

  tags = {
    Project = "nib"
    Name    = "nib-db-subnet-group"
  }
}

resource "aws_security_group" "nib_lambda_sg" {
  name        = "nib-lambda-sg"
  description = "Security group for NIB Lambda functions"
  vpc_id      = aws_vpc.nib_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "nib-lambda-sg"
    Project = "nib"
  }
}

resource "aws_security_group" "nib_rds_sg" {
  name   = "nib-rds-sg"
  vpc_id = aws_vpc.nib_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.nib_lambda_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "nib-rds-sg"
    Project = "nib"
  }
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "aws_ssm_parameter" "db_username" {
  name  = "/nib/db/username"
  type  = "String"
  value = var.db_user

  tags = {
    Project = "nib"
  }
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/nib/db/password"
  type  = "SecureString"
  value = random_password.db_password.result

  tags = {
    Project = "nib"
  }
}

resource "aws_db_instance" "nib_rds" {
  identifier             = "nib-db"
  engine                 = "postgres"
  engine_version         = "15.5"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = "nibdb"
  username               = aws_ssm_parameter.db_username.value
  password               = aws_ssm_parameter.db_password.value
  db_subnet_group_name   = aws_db_subnet_group.nib_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.nib_rds_sg.id]
  multi_az               = false
  publicly_accessible    = false
  skip_final_snapshot    = true

  tags = {
    Name    = "nib-rds"
    Project = "nib"
  }
}

resource "aws_cognito_user_pool" "nib_user_pool" {
  name = "nib-user-pool"

  password_policy {
    minimum_length    = 8
    require_numbers   = true
    require_lowercase = true
  }
}

resource "aws_cognito_user_pool_client" "nib_app_client" {
  name         = "nib-app-client"
  user_pool_id = aws_cognito_user_pool.nib_user_pool.id

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  generate_secret = false
}


