variable "aws_region" {
  type    = string
}

variable "service_name" {
  type        = string
  description = "AWS service to create the endpoint for (e.g. sns)"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the endpoint should be created"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the endpoint"
}

variable "source_security_group_ids" {
  type        = list(string)
  description = "Security groups to allow egress from"
}

variable "enable_private_dns" {
  type        = bool
  default     = true
}

variable "project" {
    type = string
    default = "nib"
}
variable "environment" {
    type = string
}