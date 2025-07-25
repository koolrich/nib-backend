locals {
  common_tags = {
    Project = var.project
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "this" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.${var.service_name}"
  vpc_endpoint_type = "Interface"
  subnet_ids        = var.subnet_ids
  security_group_ids = aws_security_group.vpc_interface_endpoints_sg.id
  private_dns_enabled = var.enable_private_dns

  tags = merge(local.common_tags, {
    Name = "${var.service_name}-endpoint"
  })
}

resource "aws_security_group" "vpc_interface_endpoints_sg" {
  name        = "nib-interface-endpoints-sg"
  description = "Security group for VPC interface endpoints"
  vpc_id      = var.vpc_id

  ingress {
    description              = "Allow HTTPS from Lambda"
    from_port                = 443
    to_port                  = 443
    protocol                 = "tcp"
    security_groups = var.source_security_group_ids
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name        = "nib-interface-endpoints-sg"
  })
}