FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md MIGRATION-2.md LICENSE ./
COPY jep_agent/ ./jep_agent/

RUN pip install --no-cache-dir -e ".[langchain,openai]"

EXPOSE 8080

CMD ["jep-agent", "web", "--host", "0.0.0.0", "--port", "8080"]
