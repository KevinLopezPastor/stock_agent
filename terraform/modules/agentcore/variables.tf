variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "ecr_repository_url" {
  description = "Full ECR repository URL"
  type        = string
}

variable "container_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "execution_role_arn" {
  description = "IAM role ARN for the AgentCore runtime"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_client_id" {
  description = "Cognito App Client ID"
  type        = string
}

variable "cognito_issuer_url" {
  description = "OIDC issuer URL for JWT validation"
  type        = string
}

variable "secrets_arn" {
  description = "ARN of the Langfuse secrets in Secrets Manager"
  type        = string
}

variable "bedrock_model_id" {
  description = "Bedrock model inference profile ID"
  type        = string
}

variable "bedrock_embedding_model_id" {
  description = "Bedrock embedding model ID"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}
