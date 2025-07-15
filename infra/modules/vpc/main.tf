locals {
  common_tags = {
    Project = var.project
    Environment = var.environment
  }
  lambda_sg_name = "nib-lambda-sg"
  db_subnet_group_name = "nib-db-subnet-group"
  db_sg_name = "nib_db_sg"
}

resource "aws_vpc" "nib_vpc" {
  cidr_block = var.cidr_block

  tags = merge(local.common_tags, {
    Name = var.name
  })
}

resource "aws_subnet" "nib_subnets" {
  for_each = var.subnets

  vpc_id            = aws_vpc.nib_vpc.id
  cidr_block        = each.value.cidr
  availability_zone = "${var.aws_region}${each.value.az}"

  tags = merge(local.common_tags, {
    Name = each.key
    Role = each.value.role
  })
}

resource "aws_security_group" "nib_lambda_sg" {
  name        = var.lambda_sg_name
  description = "Security group for NIB Lambda functions"
  vpc_id      = aws_vpc.nib_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

 tags = merge(local.common_tags, {
    Name = var.lambda_sg_name
  })
}
