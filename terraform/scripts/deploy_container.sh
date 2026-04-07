#!/usr/bin/env bash
###############################################################################
# deploy_container.sh
#
# Builds the agent Docker image (ARM64), pushes to ECR, and optionally
# triggers an AgentCore runtime update.
#
# Usage:
#   bash terraform/scripts/deploy_container.sh [IMAGE_TAG]
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - Docker with BuildX support
#   - Terraform outputs available (run from repo root after `terraform apply`)
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$REPO_ROOT/terraform"
AGENT_DIR="$REPO_ROOT/agent"

IMAGE_TAG="${1:-latest}"

echo "==> Reading Terraform outputs..."
cd "$TERRAFORM_DIR"
ECR_URL=$(terraform output -raw ecr_repository_url)
AWS_REGION=$(terraform output -raw 2>/dev/null || echo "us-east-1")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "    ECR URL:    $ECR_URL"
echo "    Region:     $AWS_REGION"
echo "    Image Tag:  $IMAGE_TAG"

echo "==> Authenticating Docker to ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Building Docker image (ARM64)..."
cd "$AGENT_DIR"
docker buildx build \
  --platform linux/arm64 \
  --tag "${ECR_URL}:${IMAGE_TAG}" \
  --load \
  .

echo "==> Pushing image to ECR..."
docker push "${ECR_URL}:${IMAGE_TAG}"

echo "==> Done! Image pushed: ${ECR_URL}:${IMAGE_TAG}"
echo ""
echo "If this is the first deployment, run 'terraform apply' again to"
echo "update the AgentCore runtime with the new image."
