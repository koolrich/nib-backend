variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "role_arn" {
  type = string
}

variable "role_session_name" {
  type = string
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

variable "db_user" {
  type = string
}

