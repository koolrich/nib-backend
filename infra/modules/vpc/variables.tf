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
  }))
  default = {
    "nib-subnet-1" = {
      cidr = "10.0.1.0/24"
      az   = "a"
    }
    "nib-subnet-2" = {
      cidr = "10.0.2.0/24"
      az   = "b"
    }
  }

  validation {
    condition = alltrue([
      for s in values(var.subnets) :
      can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/[0-9]+$", s.cidr))
    ])
    error_message = "Each 'cidr' must be a valid CIDR block (e.g., 10.0.0.0/24)."
  }

  validation {
    condition = alltrue([
      for s in values(var.subnets) :
      can(regex("^[a-z]{1}$", s.az))
    ])
    error_message = "Each 'az' must be a single lowercase letter (e.g., 'a', 'b', 'c')."
  }
}