output "secret_arn" {
  description = "ARN of the Langfuse credentials secret"
  value       = aws_secretsmanager_secret.langfuse.arn
}

output "secret_name" {
  description = "Name of the Langfuse credentials secret"
  value       = aws_secretsmanager_secret.langfuse.name
}
