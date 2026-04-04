data "aws_security_group" "rds" {
  filter {
    name   = "group-name"
    values = ["nib-db-sg"]
  }
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.nib.id]
  }
}

resource "aws_security_group_rule" "ec2_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.rds.id
  source_security_group_id = aws_security_group.ec2.id
  description              = "Allow DB access from EC2 bastion"
}
