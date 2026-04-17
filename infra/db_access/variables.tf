variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "s3_bucket" {
  type        = string
  description = "S3 bucket containing Flyway tarball and migration artifacts"
  default     = "nib-lambda-artifacts"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}
