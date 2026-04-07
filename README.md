# AI Stock Agent on AWS Bedrock AgentCore

An AI agent solution that provides real-time and historical stock price queries with RAG-powered financial analysis, deployed on AWS Bedrock AgentCore Runtime.

## Architecture

```
Client (Notebook) → Cognito (JWT Auth) → AgentCore Runtime (FastAPI)
                                              │
                                    ┌─────────┼─────────┐
                                    │         │         │
                              yfinance   FAISS KB   Bedrock LLM
                             (stocks)  (Amazon     (Claude
                                        reports)    Sonnet 4.6)
                                              │
                                          Langfuse
                                        (observability)
```

### Key Components

| Component | Technology |
|:---|:---|
| Runtime | AWS Bedrock AgentCore (serverless) |
| Auth | AWS Cognito (JWT) |
| Agent | LangGraph ReAct agent |
| LLM | Amazon Nova Lite (`amazon.nova-lite-v1:0`) |
| Knowledge Base | FAISS + Titan Embed V2 |
| Finance Data | yfinance API |
| Observability | Langfuse Cloud |
| IaC | Terraform |
| Streaming | SSE via FastAPI |

## Prerequisites

1. **AWS CLI** configured with credentials (`aws configure`)
2. **Terraform** ≥ 1.5 ([install guide](https://developer.hashicorp.com/terraform/install))
3. **Docker** with BuildX support ([install guide](https://docs.docker.com/get-docker/))
4. **Python** 3.11+ ([download](https://www.python.org/downloads/))
5. **Bedrock Model Access** — enable the following in the [Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess):
   - Amazon Nova Lite (`amazon.nova-lite-v1:0`)
   - Amazon Titan Embed Text V2 (`amazon.titan-embed-text-v2:0`)
6. **Langfuse Account** — [sign up for free](https://cloud.langfuse.com), create a project, and note your API keys

## Deployment Guide

### Step 1: Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
aws_region    = "us-east-1"
project_name  = "stock-agent"
environment   = "dev"

langfuse_public_key = "pk-lf-..."
langfuse_secret_key = "sk-lf-..."
langfuse_base_url   = "https://us.cloud.langfuse.com"
```

### Step 2: Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan     # Review the plan
terraform apply    # Type 'yes' to confirm
```

Note the outputs:
```
cognito_user_pool_id       = "us-east-1_xxxxxxx"
cognito_user_pool_client_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
ecr_repository_url         = "123456789012.dkr.ecr.us-east-1.amazonaws.com/stock-agent-dev-agent"
agentcore_endpoint_url     = "https://xxxxxxxx.agentcore.us-east-1.amazonaws.com"
```

### Step 3: Build the Knowledge Base Index

```bash
cd agent

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Build the FAISS index (downloads PDFs + generates embeddings via Bedrock)
python knowledge_base/build_index.py
```

This creates the `knowledge_base/faiss_index/` directory with the persisted vector index.

### Step 4: Build & Push Docker Image

```bash
# From the repo root
bash terraform/scripts/deploy_container.sh
```

Or manually:

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Build ARM64 image
cd agent
docker buildx build --platform linux/arm64 -t stock-agent:latest --load .

# Tag and push
docker tag stock-agent:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/stock-agent-dev-agent:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/stock-agent-dev-agent:latest
```

### Step 5: Update AgentCore Runtime

After pushing the image, re-apply Terraform to update the runtime:

```bash
cd terraform
terraform apply
```

### Step 6: Run the Demo Notebook

1. Open `notebook/demo.ipynb` in Jupyter
2. Update the configuration cell with your Terraform outputs
3. Execute all cells to:
   - Create a test user in Cognito
   - Authenticate and obtain JWT tokens
   - Run all 5 required queries with streaming
   - Verify Langfuse traces

## Project Structure

```
├── README.md                           # This file
├── terraform/                          # Infrastructure as Code
│   ├── main.tf                         # Root module
│   ├── variables.tf                    # Input variables
│   ├── outputs.tf                      # Exported values
│   ├── terraform.tfvars.example        # Template
│   ├── modules/
│   │   ├── cognito/                    # User pool & app client
│   │   ├── ecr/                        # Container registry
│   │   ├── iam/                        # Execution role & policies
│   │   ├── secrets/                    # Langfuse credentials
│   │   └── agentcore/                  # Runtime & endpoint
│   └── scripts/
│       └── deploy_container.sh         # Build & push helper
├── agent/                              # Python agent source
│   ├── Dockerfile                      # ARM64 container
│   ├── requirements.txt                # Dependencies
│   ├── main.py                         # FastAPI endpoints
│   ├── agent/
│   │   ├── graph.py                    # LangGraph ReAct agent
│   │   ├── state.py                    # Agent state schema
│   │   ├── prompts.py                  # System prompts
│   │   ├── observability.py            # Langfuse integration
│   │   └── tools/
│   │       ├── stock_tools.py          # yfinance tools
│   │       └── knowledge_base.py       # FAISS retriever tool
│   ├── knowledge_base/
│   │   └── build_index.py              # Index builder script
│   └── auth/
│       └── cognito.py                  # JWT validation
├── notebook/
│   ├── demo.ipynb                      # Demonstration notebook
│   └── screenshots/                    # Langfuse screenshots
└── .gitignore
```

## API Reference

### `GET /ping`
Health check endpoint.
```json
{"status": "healthy"}
```

### `POST /invocations`
Agent invocation with SSE streaming.

**Headers:**
```
Authorization: Bearer <cognito_jwt_token>
Content-Type: application/json
Accept: text/event-stream
```

**Request Body:**
```json
{
  "query": "What is the stock price for Amazon right now?",
  "thread_id": "optional-uuid-for-session"
}
```

**Response:** Server-Sent Events stream with events:
- `token` — LLM response tokens (streamed incrementally)
- `tool_result` — Tool execution results
- `status` — Node transition updates
- `done` — Stream completion signal
- `error` — Error messages

## Local Development

Run the agent locally without AgentCore:

```bash
cd agent
export BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-6"
export AWS_REGION="us-east-1"
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_BASE_URL="https://us.cloud.langfuse.com"

# Build the FAISS index first
python knowledge_base/build_index.py

# Run FastAPI locally (Cognito auth disabled when COGNITO_USER_POOL_ID is unset)
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Test with curl:
```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the stock price for AMZN?"}'
```

## Observability & Evidence

The solution uses **Langfuse** to provide a "glass box" view of the agent's reasoning process.

### How to obtain real screenshots for the Boss's Checklist:

1.  **Execute the Queries**: Run all 5 query cells in `notebook/demo.ipynb`. Each call sends a trace to Langfuse.
2.  **Access the Dashboard**: Login to [cloud.langfuse.com](https://cloud.langfuse.com) and enter your project.
3.  **Capture Traces List**:
    -   Navigate to the **"Traces"** tab.
    -   You will see a list of executions named `stock-agent-call-final-70`.
    -   Take a screenshot and save it as `notebook/screenshots/langfuse_traces.png`.
4.  **Capture Trace Detail**:
    -   Click on any trace from the list to see the detailed span view (LLM calls, FAISS retrieval, yfinance tools).
    -   Take a screenshot and save it as `notebook/screenshots/langfuse_trace_detail.png`.

By saving the files with these exact names, the links in `demo.ipynb` will automatically display your real production data.

### Cognito Identity Verification

The notebook includes a JWT decoder cell. This serves as **proof of authentication**. It demonstrates that the agent successfully extracted the `sub` (unique ID) and `email` from the Cognito-validated token before proceeding with the query.

## Cleanup

```bash
cd terraform
terraform destroy
```

This removes all AWS resources (Cognito, ECR, AgentCore, IAM, Secrets Manager).

## License

This project is for demonstration purposes.
