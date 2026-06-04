# CertMesh — container image for Foundry Agent Service Hosted Agents.
# Secrets are NEVER baked in: configuration comes from environment / managed
# identity at runtime (see deploy_hosted_agent.md).

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install dependencies first (better layer caching). Include the [azure] extra so
# the real Foundry / Agent Framework / Foundry IQ paths light up when configured.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[azure]"

# Application code + synthetic data (no secrets).
COPY app ./app
COPY data ./data

# Run as a non-root user.
RUN useradd --create-home --uid 10001 certmesh && chown -R certmesh:certmesh /app
USER certmesh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"

# The orchestrator is served behind the FastAPI gateway; Foundry Agent Service
# routes requests to this endpoint.
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
