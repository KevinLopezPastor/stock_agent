# Cognito
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito app-client ID (public, no secret)"
  value       = module.cognito.user_pool_client_id
}

output "cognito_issuer_url" {
  description = "OIDC issuer URL for the Cognito User Pool"
  value       = module.cognito.issuer_url
}

# ECR
output "ecr_repository_url" {
  description = "ECR repository URL for the agent container image"
  value       = module.ecr.repository_url
}

# AgentCore
output "agentcore_endpoint_url" {
  description = "Public invoke URL for the AgentCore runtime endpoint"
  value       = module.agentcore.endpoint_url
}

output "agentcore_runtime_id" {
  description = "AgentCore runtime resource ID"
  value       = module.agentcore.runtime_id
}
