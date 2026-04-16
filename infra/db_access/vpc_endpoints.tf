resource "aws_security_group" "vpc_endpoints" {
  name        = "nib-db-access-endpoints-sg-${var.env}"
  description = "Security group for SSM VPC interface endpoints"
  vpc_id      = data.aws_vpc.nib.id

  ingress {
    description     = "Allow HTTPS from EC2 instance"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "nib-db-access-endpoints-sg-${var.env}"
    Project     = "nib"
    Environment = var.env
  }
}

data "aws_security_group" "shared_endpoints" {
  filter {
    name   = "group-name"
    values = ["nib-interface-endpoints-sg-${var.env}"]
  }
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.nib.id]
  }
}

resource "aws_security_group_rule" "ec2_to_ssm_endpoint" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.shared_endpoints.id
  source_security_group_id = aws_security_group.ec2.id
  description              = "Allow SSM access from EC2 bastion"
}

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id              = data.aws_vpc.nib.id
  service_name        = "com.amazonaws.${var.aws_region}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [data.aws_subnet.private.id]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Project     = "nib"
    Environment = var.env
  }
}

resource "aws_vpc_endpoint" "ec2messages" {
  vpc_id              = data.aws_vpc.nib.id
  service_name        = "com.amazonaws.${var.aws_region}.ec2messages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [data.aws_subnet.private.id]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Project     = "nib"
    Environment = var.env
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.nib.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [data.aws_route_table.private.id]

  tags = {
    Project     = "nib"
    Environment = var.env
  }
}
