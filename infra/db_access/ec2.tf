resource "aws_security_group" "ec2" {
  name        = "nib-db-access-sg-${var.env}"
  description = "Security group for NIB DB access EC2 instance"
  vpc_id      = data.aws_vpc.nib.id

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "nib-db-access-sg-${var.env}"
    Project     = "nib"
    Environment = var.env
  }
}

resource "aws_instance" "nib_db_access" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnet.private.id
  iam_instance_profile   = aws_iam_instance_profile.nib_db_access_profile.name
  vpc_security_group_ids = [aws_security_group.ec2.id]

  tags = {
    Name        = "NIBDBAccessInstance-${var.env}"
    Project     = "nib"
    Environment = var.env
  }

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }
}
