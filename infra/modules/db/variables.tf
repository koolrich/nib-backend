variable "db_user" {
  type        = string
  description = "Database username"
}

variable "db_name" {
  type        = string
  description = "Database name"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for DB subnet group"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "lambda_sg_id" {
  type        = string
  description = "Lambda security group ID"
}

variable "db_sg_name" {
  type = string
  description = "Database security group name"
}

variable "project" {
  type        = string
  description = "Project name"
}

variable "environment" {
  type        = string
  description = "Environment"
}

variable "db_subnet_group_name" {
  type        = string
  description = "Name of DB subnet group"
}