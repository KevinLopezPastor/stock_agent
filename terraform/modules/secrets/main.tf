###############################################################################
# Secrets Manager — Langfuse Credentials
###############################################################################
resource "aws_secretsmanager_secret" "langfuse" {
  name                    = "${var.project_name}-${var.environment}-langfuse"
  description             = "Langfuse observability credentials"
  recovery_window_in_days = 0 # Allow immediate deletion in dev

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "langfuse" {
  secret_id = aws_secretsmanager_secret.langfuse.id

  secret_string = jsonencode({
    LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
    LANGFUSE_SECRET_KEY = var.langfuse_secret_key
    LANGFUSE_BASE_URL   = var.langfuse_base_url
  })
}
