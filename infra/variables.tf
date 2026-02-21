variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "hack-europe"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet 1"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_2_cidr" {
  description = "CIDR block for public subnet 2"
  type        = string
  default     = "10.0.2.0/24"
}

variable "app_port" {
  description = "Port exposed by the application"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/health"
}

variable "fargate_cpu" {
  description = "Fargate instance CPU units to provision (512 = 0.5 vCPU)"
  type        = number
  default     = 512
}

variable "fargate_memory" {
  description = "Fargate instance memory to provision (in MiB)"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Number of instances of the task definition to place and keep running"
  type        = number
  default     = 1
}

variable "container_name" {
  description = "Name of the container"
  type        = string
  default     = "hack-europe-app"
}

variable "container_environment" {
  description = "Base environment variables for the container (optional override in variables.tfvars)"
  type        = list(object({
    name  = string
    value = string
  }))
  sensitive = true
  default = [
    { name = "PORT", value = "8000" }
  ]
}

variable "supabase_postgres_url" {
  description = "Supabase Postgres connection URL (set in terraform.auto.tfvars)"
  type        = string
  sensitive   = true
}

variable "supabase_url" {
  description = "Supabase project URL (set in terraform.auto.tfvars)"
  type        = string
  sensitive   = true
}
 