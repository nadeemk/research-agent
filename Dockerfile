FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

ENV PORT=8080
EXPOSE 8080

# ANTHROPIC_API_KEY and RESEARCH_AGENT_API_KEY are injected at runtime
# (Cloud Run env vars / Secret Manager, AWS Fargate task def secrets, etc.)
# — never bake them into the image.
CMD ["sh", "-c", "uvicorn research_agent.api:app --host 0.0.0.0 --port ${PORT}"]
