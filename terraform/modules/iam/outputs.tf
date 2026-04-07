output "agentcore_role_arn" {
  description = "ARN of the AgentCore execution IAM role"
  value       = aws_iam_role.agentcore_execution.arn
}

output "agentcore_role_name" {
  description = "Name of the AgentCore execution IAM role"
  value       = aws_iam_role.agentcore_execution.name
}
