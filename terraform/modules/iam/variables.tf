variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "ecr_repository_arn" {
  description = "ARN of the ECR repository the agent will pull from"
  type        = string
}

variable "secrets_arn" {
  description = "ARN of the Secrets Manager secret containing API keys"
  type        = string
}
