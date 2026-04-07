output "runtime_id" {
  description = "AgentCore Runtime ID"
  value       = aws_bedrockagentcore_agent_runtime.main.agent_runtime_id
}

output "runtime_arn" {
  description = "AgentCore Runtime ARN"
  value       = aws_bedrockagentcore_agent_runtime.main.agent_runtime_arn
}

output "endpoint_arn" {
  description = "AgentCore Runtime Endpoint ARN"
  value       = aws_bedrockagentcore_agent_runtime_endpoint.main.agent_runtime_endpoint_arn
}

output "endpoint_url" {
  description = "AgentCore Runtime public endpoint URL (derived from endpoint ARN)"
  value       = aws_bedrockagentcore_agent_runtime_endpoint.main.agent_runtime_endpoint_arn
}
