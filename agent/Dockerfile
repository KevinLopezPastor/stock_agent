FROM python:3.11-slim

# System dependencies (Minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code
COPY . .

# Ensure logs are sent immediately
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# Health check
HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=5 \
  CMD curl -f http://127.0.0.1:8080/ping || exit 1

# Re-enable OTEL wrapper to capture stdout logs for AgentCore
# Disable Traces/Metrics to avoid ADOT 403 Forbidden errors when X-Ray is not fully accessible
ENV OTEL_TRACES_EXPORTER=none
ENV OTEL_METRICS_EXPORTER=none
# Let the Bedrock platform intercept standard logging via the default OTLP handler
ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

CMD ["opentelemetry-instrument", "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
