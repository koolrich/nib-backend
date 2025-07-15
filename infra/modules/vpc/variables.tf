variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "cidr_block" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "project" {
  type        = string
  description = "Project name tag"
}

variable "environment" {
  type        = string
  description = "Environment"
}


variable "name" {
  type        = string
  description = "VPC name tag"
}

variable "subnets" {
  description = "Map of subnet configs with CIDR and AZ"
  type = map(object({
    cidr = string
    az   = string
    role = string
  }))
  
}


variable "lambda_sg_name" {
  type = string
  description = "Security group name for lambda"
}