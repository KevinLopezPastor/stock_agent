###############################################################################
# General
###############################################################################
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project identifier used in resource names"
  type        = string
  default     = "stock-agent"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

###############################################################################
# Bedrock / LLM
###############################################################################
variable "bedrock_model_id" {
  description = "Amazon Bedrock model inference profile ID"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "bedrock_embedding_model_id" {
  description = "Amazon Bedrock embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

###############################################################################
# Langfuse
###############################################################################
variable "langfuse_public_key" {
  description = "Langfuse public key"
  type        = string
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key"
  type        = string
  sensitive   = true
}

variable "langfuse_base_url" {
  description = "Langfuse base URL"
  type        = string
  default     = "https://us.cloud.langfuse.com"
}

###############################################################################
# Container / AgentCore
###############################################################################
variable "container_image_tag" {
  description = "Tag for the agent Docker image in ECR"
  type        = string
  default     = "latest"
}
