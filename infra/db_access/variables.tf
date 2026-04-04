variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "ami_id" {
  type        = string
  description = "AMI ID for the EC2 instance (should have connect-db and migration scripts baked in)"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "role_arn" {
  type    = string
  default = "arn:aws:iam::021891595998:role/TerraformUserRole"
}

variable "role_session_name" {
  type    = string
  default = "terraform-db-access-session"
}
