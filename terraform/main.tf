# Terraform Configuration
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.32"
    }
  }

  # For production, use an S3 + DynamoDB backend:
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "stock-agent/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

# Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data Sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Modules
# Cognito
module "cognito" {
  source = "./modules/cognito"

  project_name = var.project_name
  environment  = var.environment
}

# ECR
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# Secrets Manager
module "secrets" {
  source = "./modules/secrets"

  project_name        = var.project_name
  environment         = var.environment
  langfuse_public_key = var.langfuse_public_key
  langfuse_secret_key = var.langfuse_secret_key
  langfuse_base_url   = var.langfuse_base_url
}

# IAM
module "iam" {
  source = "./modules/iam"

  project_name       = var.project_name
  environment        = var.environment
  ecr_repository_arn = module.ecr.repository_arn
  secrets_arn        = module.secrets.secret_arn
}

# AgentCore
module "agentcore" {
  source = "./modules/agentcore"

  project_name               = var.project_name
  environment                = var.environment
  aws_region                 = var.aws_region
  ecr_repository_url         = module.ecr.repository_url
  container_image_tag        = var.container_image_tag
  execution_role_arn         = module.iam.agentcore_role_arn
  cognito_user_pool_id       = module.cognito.user_pool_id
  cognito_client_id          = module.cognito.user_pool_client_id
  cognito_issuer_url         = module.cognito.issuer_url
  secrets_arn                = module.secrets.secret_arn
  bedrock_model_id           = var.bedrock_model_id
  bedrock_embedding_model_id = var.bedrock_embedding_model_id
}
