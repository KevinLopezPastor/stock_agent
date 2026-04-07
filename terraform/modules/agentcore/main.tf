resource "aws_bedrockagentcore_agent_runtime" "main" {
  agent_runtime_name = "${replace(var.project_name, "-", "_")}_${var.environment}_runtime"
  description        = "Stock analysis agent runtime"

  role_arn = var.execution_role_arn

  # Container artifact configuration — pull from ECR
  agent_runtime_artifact {
    container_configuration {
      container_uri = "${var.ecr_repository_url}:${var.container_image_tag}"
    }
  }

  # Environment variables injected into the container — adding PYTHONUNBUFFERED for real-time logs
  environment_variables = {
    AWS_REGION                 = var.aws_region
    COGNITO_USER_POOL_ID       = var.cognito_user_pool_id
    COGNITO_CLIENT_ID          = var.cognito_client_id
    COGNITO_ISSUER_URL         = var.cognito_issuer_url
    LANGFUSE_SECRET_ARN        = var.secrets_arn
    BEDROCK_MODEL_ID           = var.bedrock_model_id
    BEDROCK_EMBEDDING_MODEL_ID = var.bedrock_embedding_model_id
    LOG_LEVEL                  = "INFO"
    PYTHONUNBUFFERED           = "1"
    UPDATE_TRIGGER             = "73"
  }

  # Network mode — the runtime needs outbound internet for yfinance & Langfuse
  network_configuration {
    network_mode = "PUBLIC"
  }

  # JWT authorizer using Cognito OIDC discovery
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url    = "${var.cognito_issuer_url}/.well-known/openid-configuration"
      allowed_audience = [var.cognito_client_id]
    }
  }

  timeouts {
    create = "10m"
    update = "10m"
    delete = "10m"
  }
}

###############################################################################
# AgentCore Runtime Endpoint
###############################################################################
resource "aws_bedrockagentcore_agent_runtime_endpoint" "main" {
  agent_runtime_id      = aws_bedrockagentcore_agent_runtime.main.agent_runtime_id
  agent_runtime_version = aws_bedrockagentcore_agent_runtime.main.agent_runtime_version
  name                  = "${replace(var.project_name, "-", "_")}_${var.environment}_endpoint"
  description           = "Public endpoint for the stock agent"

  timeouts {
    create = "10m"
    delete = "10m"
  }
}
